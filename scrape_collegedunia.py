# # scrape_collegedunia.py

# import logging
# import asyncio
# import re
# from typing import List, Dict, Tuple

# from bs4 import BeautifulSoup

# from utils import delay, absolute_url

# logger = logging.getLogger(__name__)

# TARGET_CONTAINER_CLASS = (
#     "jsx-2802116687 jsx-493108142 jsx-946107936 about-section-reserve-height "
#     "listing-article-new-design-clg exam-page"
# )

# OPTION_PREFIX_RE = re.compile(r"^\s*\(?\s*([0-9]+|[A-Da-d])[\).]\s*")

# MAX_CONCURRENT_SOLUTIONS = 4


# def _extract_correct_answer_and_link(ans_div) -> Tuple[str, str]:
    
#     if not ans_div:
#         return "", ""
 
#     correct_answer = ""
#     solution_link = ""

#     strong_cor = ans_div.find("strong", string=lambda s: s and "Correct Answer" in s)

#     if strong_cor:
#         ans_text = ans_div.get_text("\n", strip=True)
#         if "Correct Answer" in ans_text:
#             idx = ans_text.find("Correct Answer")
#             segment = ans_text[idx:].split("View Solution")[0]
#             correct_answer = segment.replace("Correct Answer:", "").strip()
#         else:
#             nxt = strong_cor.next_sibling
#             if nxt:
#                 correct_answer = str(nxt).strip()
#     else:
#         all_lines = [ln.strip() for ln in ans_div.get_text("\n").splitlines() if ln.strip()]
#         if all_lines:
#             correct_answer = all_lines[0]

#     a_tag = ans_div.find("a")
#     if a_tag and a_tag.get("href"):
#         solution_link = absolute_url("https://collegedunia.com", a_tag.get("href"))

#     return correct_answer, solution_link


# def _collect_images_with_parents(root, base_url: str) -> List[Dict]:
    
#     if root is None:
#         return []

#     items: List[Dict] = []

#     for img in root.find_all("img"):
#         src = (
#             img.get("src")
#             or img.get("data-src")
#             or img.get("data-original")
#             or img.get("data-lazy-src")
#         )
#         if not src:
#             continue

#         src_abs = absolute_url(base_url, src)
#         alt = img.get("alt") or ""

#         parent = img
#         for ancestor in img.parents:
#             if ancestor.name in ("p", "div", "li", "span"):
#                 parent = ancestor
#                 break

#         items.append(
#             {
#                 "src": src_abs,
#                 "alt": alt,
#                 "parent_name": parent.name,
#                 "parent_html": str(parent),
#             }
#         )

#     return items



# def _parse_solution_page_structured(html: str, page_url: str) -> Dict:
    
#     soup = BeautifulSoup(html, "html.parser")

#     def _has_classes(val, required: set) -> bool:
#         if not val:
#             return False
#         if isinstance(val, (list, tuple, set)):
#             classes = set(val)
#         else:
#             classes = set(str(val).split())
#         return all(cls in classes for cls in required)

#     # ---------- QUESTION BLOCK ----------
#     question_block = (
#         soup.select_one("div.custom-content-section.question")
#         or soup.select_one("div.content-section.question")
#     )
#     if not question_block:
#         span_q = soup.find("span", string=lambda s: s and "Question" in s)
#         if span_q:
#             question_block = span_q.find_parent("div")
#         else:
#             question_block = soup.body or soup

#     question_ck = question_block.select_one(".ck-content") or question_block
#     question_text = question_ck.get_text(" ", strip=True)
#     question_html = str(question_ck)
#     question_images = _collect_images_with_parents(question_ck, page_url)

#     top_label = soup.find(
#         "div",
#         class_=lambda c: _has_classes(c, {"content-color", "text-italic"}),
#     )
#     question_number_text = top_label.get_text(" ", strip=True) if top_label else ""

#     # ---------- OPTIONS BLOCK ----------
#     options: List[Dict] = []

#     ul_mcq = soup.find("ul", class_=lambda c: _has_classes(c, {"mcq"}))
#     if not ul_mcq:
#         ul_mcq = soup.find("ul", class_=lambda c: c and "mcq" in str(c))

#     if ul_mcq:
#         for li in ul_mcq.find_all("li", id=re.compile(r"^option"), recursive=False):
#             label = li.get("data-csm-title") or li.get("data-ga-title") or ""
#             ck = li.select_one(".ck-content") or li
#             opt_text = ck.get_text(" ", strip=True)
#             opt_html = str(ck)
#             opt_images = _collect_images_with_parents(ck, page_url)

#             options.append(
#                 {
#                     "label": label,       # e.g. "A", "B", "C", "D"
#                     "text": opt_text,
#                     "html": opt_html,
#                     "images": opt_images,
#                     "is_correct": False,   # will be updated below
#                 }
#             )
#     # ---------- CORRECT ANSWER TEXT & MARK OPTIONS ----------
#     correct_answer_text = ""
#     correct_label = ""


#     h2_corr = None
#     for h2 in soup.find_all("h2"):
#         txt = h2.get_text(" ", strip=True).lower()
#         if "correct option" in txt or "correct answer" in txt:
#             h2_corr = h2
#             break

#     if h2_corr:
#         spans = h2_corr.find_all("span")
#         if len(spans) >= 2:
#             # second <span> contains the actual option letter (A/B/C/D)
#             correct_answer_text = spans[1].get_text(" ", strip=True).strip()
#             correct_label = correct_answer_text.upper()
#         else:
#             # fallback: use full h2 text and regex
#             correct_answer_text = h2_corr.get_text(" ", strip=True)
#             m = re.search(r"\b([A-D])\b", correct_answer_text.upper())
#             if m:
#                 correct_label = m.group(1)
#     else:
#         # secondary fallback: any text node containing "correct option"/"correct answer"
#         corr_label_node = soup.find(
#             string=lambda s: s
#             and "correct" in s.lower()
#             and ("option" in s.lower() or "answer" in s.lower())
#         )
#         if corr_label_node:
#             corr_parent = corr_label_node.parent
#             correct_answer_text = corr_parent.get_text(" ", strip=True)
#             m = re.search(r"\b([A-D])\b", correct_answer_text.upper())
#             if m:
#                 correct_label = m.group(1)

#     # Mark the correct option (default False, True only for matching label)
#     if correct_label:
#         for opt in options:
#             lbl = (opt.get("label") or "").strip().upper()
#             opt["is_correct"] = (lbl == correct_label)

        
#     # ---------- HINT BLOCK ----------
#     hint_text = ""
#     hint_html = ""
#     hint_images: List[Dict] = []
    
#     hint_block = soup.find("div", class_=lambda c: c and "dark-bg" in c)
    
#     if hint_block:
#         ck = hint_block.find("div", class_=lambda c: c and "ck-content" in c)
#         if ck:
#             hint_text = ck.get_text(" ", strip=True)
#             hint_html = str(ck)
#             hint_images = _collect_images_with_parents(ck, page_url)
            
    
#     # ---------- SOLUTION / EXPLANATION BLOCK ----------
#     solution_text = ""
#     solution_html = ""
#     solution_images: List[Dict] = []

#     h2_sol = None
#     for h2 in soup.find_all("h2"):
#         txt = h2.get_text(" ", strip=True).lower()
#         if "solution" in txt or "explanation" in txt:
#             h2_sol = h2
#             break

#     if h2_sol:
#         sol_container = h2_sol.find_parent("div")
#         sol_ck = sol_container.find("div", class_="ck-content") or sol_container
#     else:
#         sol_ck = question_block.find_next("div", class_="ck-content") or question_block

#     solution_text = sol_ck.get_text(" ", strip=True)
#     solution_html = str(sol_ck)
#     solution_images = _collect_images_with_parents(sol_ck, page_url)
    
#     # ---------- CORRECT ANSWER TEXT ----------
#     # correct_answer_text = ""
#     # corr_label = soup.find(string=lambda s: s and "Correct Answer" in s)
#     # if corr_label:
#     #     corr_parent = corr_label.parent
#     #     correct_answer_text = (
#     #         corr_parent.get_text(" ", strip=True)
#     #         .replace("Correct Answer:", "")
#     #         .strip()
#     #     )

    
#     return {
#         "question_number_text": question_number_text,
#         "question_text": question_text,
#         "question_html": question_html,
#         "question_images": question_images,
#         "hint_text": hint_text,
#         "hint_html": hint_html,
#         "hint_images": hint_images,
#         "options": options,
#         "correct_answer_text": correct_answer_text,
#         "solution_text": solution_text,
#         "solution_html": solution_html,
#         "solution_images": solution_images,
#     }


# async def _scrape_single_solution(
#     context,
#     qid: int,
#     solution_url: str,
#     sem: asyncio.Semaphore,
#     timeout: int = 30000,
# ) -> Dict:
#     async with sem:
#         page = await context.new_page()
#         try:
#             await delay(1.0, 3.0)
#             resp = await page.goto(
#                 solution_url,
#                 timeout=timeout,
#                 wait_until="domcontentloaded",
#             )
#             if resp is None:
#                 logger.warning(
#                     "Navigation to solution page returned None: %s",
#                     solution_url,
#                 )

#             try:
#                 await page.wait_for_selector(
#                     "main, article, .solution, .answer-section, body",
#                     timeout=8000,
#                 )
#             except Exception:
#                 await page.wait_for_timeout(2500)

#             # rendered_html = ""
#             # for sel in ["main", "article", ".solution", ".answer-section", "body"]:
#             #     try:
#             #         h = await page.query_selector(sel)
#             #     except Exception:
#             #         h = None
#             #     if h:
#             #         rendered_html = await h.inner_html()
#             #         break

#             # if not rendered_html:
#             rendered_html = await page.content()

#             page_url = page.url

#             structured = _parse_solution_page_structured(rendered_html, page_url)

#             await delay(0.8, 2.0)

#             result: Dict = {
#                 "id": qid,
#                 "solution_link": solution_url,
#                 "solution_page": page_url,
#                 "status": "ok",
#             }
#             result.update(structured)
#             return result

#         except Exception as exc:
#             logger.exception("Failed to scrape solution page %s: %s", solution_url, exc)
#             return {
#                 "id": qid,
#                 "solution_link": solution_url,
#                 "solution_page": solution_url,
#                 "status": "error",
#                 "error": str(exc),
#             }
#         finally:
#             try:
#                 await page.close()
#             except Exception:
#                 pass


# async def scrape_collegedunia_questions(context, page) -> Dict:
    
#     try:
#         await page.wait_for_timeout(1500)
#         html = await page.content()
#         soup = BeautifulSoup(html, "html.parser")

#         container = soup.find(
#             "div",
#             class_=lambda x: x and TARGET_CONTAINER_CLASS in x,
#         )
#         if not container:
#             container = soup.find(
#                 "div",
#                 class_=lambda x: x
#                 and "exam-page" in x
#                 and "listing-article-new-design-clg" in x,
#             )

#         if not container:
#             logger.warning("Main container not found on page.")
#             return {"solution_urls": [], "solutions_detail": []}

#         question_divs = container.find_all("div", class_="question")
#         logger.info("Found %d question blocks", len(question_divs))

#         # --------- First array: just URLs ----------
#         solution_urls: List[Dict] = []
#         q_index = 0

#         for qdiv in question_divs:
#             q_index += 1
#             ans_div = qdiv.find("div", class_="answer-section")
#             _, solution_link = _extract_correct_answer_and_link(ans_div)

#             solution_urls.append(
#                 {
#                     "id": q_index,
#                     "solution_link": solution_link or "",
#                 }
#             )

#         # --------- Second array: visit each solution URL ----------
#         sem = asyncio.Semaphore(MAX_CONCURRENT_SOLUTIONS)
#         tasks: List[asyncio.Task] = []

#         for entry in solution_urls:
#             qid = entry["id"]
#             link = entry["solution_link"]
#             if not link:
#                 continue
#             tasks.append(
#                 asyncio.create_task(
#                     _scrape_single_solution(context, qid, link, sem)
#                 )
#             )

        
#         solutions_detail: List[Dict] = []
#         if tasks:
#             logger.info(
#                 "Scraping %d solution pages with concurrency=%d",
#                 len(tasks),
#                 MAX_CONCURRENT_SOLUTIONS,
#             )
#             results = await asyncio.gather(*tasks, return_exceptions=True)
#             for res in results:
#                 if isinstance(res, Exception):
#                     logger.error("Unexpected error in solution task: %s", res)
#                     continue
#                 solutions_detail.append(res)

#         await delay(0.4, 1.0)

#         return {
#             "solution_urls": solution_urls,
#             "solutions_detail": solutions_detail,
#         }

#     except Exception as exc:
#         logger.exception("scrape_collegedunia_questions failed: %s", exc)
#         return {"solution_urls": [], "solutions_detail": []}
# scrape_collegedunia.py

import logging
import asyncio
import re
from typing import List, Dict, Tuple

from bs4 import BeautifulSoup

from utils import delay, absolute_url

logger = logging.getLogger(__name__)

TARGET_CONTAINER_CLASS = (
    "jsx-2802116687 jsx-493108142 jsx-946107936 about-section-reserve-height "
    "listing-article-new-design-clg exam-page"
)

OPTION_PREFIX_RE = re.compile(r"^\s*\(?\s*([0-9]+|[A-Da-d])[\).]\s*")
MAX_CONCURRENT_SOLUTIONS = 4

def _extract_correct_answer_and_link(ans_div) -> Tuple[str, str]:
    
    if not ans_div:
        return "", ""

    correct_answer = ""
    solution_link = ""

    strong_cor = ans_div.find("strong", string=lambda s: s and "Correct Answer" in s)

    if strong_cor:
        ans_text = ans_div.get_text("\n", strip=True)
        if "Correct Answer" in ans_text:
            idx = ans_text.find("Correct Answer")
            segment = ans_text[idx:].split("View Solution")[0]
            correct_answer = segment.replace("Correct Answer:", "").strip()
        else:
            nxt = strong_cor.next_sibling
            if nxt:
                correct_answer = str(nxt).strip()
    else:
        all_lines = [ln.strip() for ln in ans_div.get_text("\n").splitlines() if ln.strip()]
        if all_lines:
            correct_answer = all_lines[0]

    a_tag = ans_div.find("a")
    if a_tag and a_tag.get("href"):
        solution_link = absolute_url("https://collegedunia.com", a_tag.get("href"))

    return correct_answer, solution_link

def _collect_images_with_parents(root, base_url: str) -> List[Dict]:
    """
    From a root BeautifulSoup node, collect all <img> tags with:
      - absolute src
      - alt text
      - parent tag name
      - parent HTML snippet (e.g. full <p>...</p>)

    This is used for question, options, hint, and solution sections.
    """
    if root is None:
        return []

    items: List[Dict] = []

    for img in root.find_all("img"):
        src = (
            img.get("src")
            or img.get("data-src")
            or img.get("data-original")
            or img.get("data-lazy-src")
        )
        if not src:
            continue

        src_abs = absolute_url(base_url, src)
        alt = img.get("alt") or ""

        parent = img
        for ancestor in img.parents:
            if ancestor.name in ("p", "div", "li", "span"):
                parent = ancestor
                break

        items.append(
            {
                "src": src_abs,
                "alt": alt,
                "parent_name": parent.name,
                "parent_html": str(parent),
            }
        )

    return items


def _parse_solution_page_structured(html: str, page_url: str) -> Dict:
    
    soup = BeautifulSoup(html, "html.parser")

    def _has_classes(val, required: set) -> bool:
        if not val:
            return False
        if isinstance(val, (list, tuple, set)):
            classes = set(val)
        else:
            classes = set(str(val).split())
        return all(cls in classes for cls in required)

    # ---------- QUESTION BLOCK ----------
    question_block = (
        soup.select_one("div.custom-content-section.question")
        or soup.select_one("div.content-section.question")
    )
    if not question_block:
        span_q = soup.find("span", string=lambda s: s and "Question" in s)
        if span_q:
            question_block = span_q.find_parent("div")
        else:
            question_block = soup.body or soup

    question_ck = question_block.select_one(".ck-content") or question_block
    question_text = question_ck.get_text(" ", strip=True)
    question_html = str(question_ck)
    question_images = _collect_images_with_parents(question_ck, page_url)

    # attempt to read a "Question 7" label if present
    top_label = soup.find(
        "div",
        class_=lambda c: _has_classes(c, {"content-color", "text-italic"}),
    )
    question_number_text = top_label.get_text(" ", strip=True) if top_label else ""

    # ---------- OPTIONS BLOCK ----------
    options: List[Dict] = []

    ul_mcq = soup.find("ul", class_=lambda c: _has_classes(c, {"mcq"}))
    if not ul_mcq:
        ul_mcq = soup.find("ul", class_=lambda c: c and "mcq" in str(c))

    if ul_mcq:
        # each li: id="option1/2/3/4", data-csm-title="A/B/C/D", and contains a .ck-content
        for li in ul_mcq.find_all("li", id=re.compile(r"^option"), recursive=False):
            label = li.get("data-csm-title") or li.get("data-ga-title") or ""
            ck = li.select_one(".ck-content") or li
            opt_text = ck.get_text(" ", strip=True)
            opt_html = str(ck)
            opt_images = _collect_images_with_parents(ck, page_url)

            options.append(
                {
                    "label": label,       # e.g. "A", "B", "C", "D"
                    "text": opt_text,
                    "html": opt_html,
                    "images": opt_images,
                    "is_correct": False,   # will be updated below
                }
            )

    # ---------- CORRECT ANSWER TEXT & MARK OPTIONS ----------
    correct_answer_text = ""
    correct_label = ""

    # Prefer explicit <h2> with two spans: "The Correct Option is" + "B"
    h2_corr = None
    for h2 in soup.find_all("h2"):
        txt = h2.get_text(" ", strip=True).lower()
        if "correct option" in txt or "correct answer" in txt:
            h2_corr = h2
            break

    if h2_corr:
        spans = h2_corr.find_all("span")
        if len(spans) >= 2:
            # second <span> contains the actual option letter (A/B/C/D)
            correct_answer_text = spans[1].get_text(" ", strip=True).strip()
            correct_label = correct_answer_text.upper()
        else:
            # fallback: use full h2 text and regex
            correct_answer_text = h2_corr.get_text(" ", strip=True)
            m = re.search(r"\b([A-D])\b", correct_answer_text.upper())
            if m:
                correct_label = m.group(1)
    else:
        # secondary fallback: any text node containing "correct option"/"correct answer"
        corr_label_node = soup.find(
            string=lambda s: s
            and "correct" in s.lower()
            and ("option" in s.lower() or "answer" in s.lower())
        )
        if corr_label_node:
            corr_parent = corr_label_node.parent
            correct_answer_text = corr_parent.get_text(" ", strip=True)
            m = re.search(r"\b([A-D])\b", correct_answer_text.upper())
            if m:
                correct_label = m.group(1)

    # Mark the correct option (default False, True only for matching label)
    if correct_label:
        for opt in options:
            lbl = (opt.get("label") or "").strip().upper()
            opt["is_correct"] = (lbl == correct_label)

    # ---------- HINT BLOCK ----------
    hint_text = ""
    hint_html = ""
    hint_images: List[Dict] = []

    # Hint is inside <div class="... dark-bg ...">
    hint_block = soup.find("div", class_=lambda c: c and "dark-bg" in c)
    if hint_block:
        ck = hint_block.find("div", class_=lambda c: c and "ck-content" in c)
        if ck:
            hint_text = ck.get_text(" ", strip=True)
            hint_html = str(ck)
            hint_images = _collect_images_with_parents(ck, page_url)

    # ---------- SOLUTION / EXPLANATION BLOCK ----------
    solution_text = ""
    solution_html = ""
    solution_images: List[Dict] = []

    sol_ck = None

    # 1) FIRST PRIORITY → <div> whose class contains "solution"
    sol_block = soup.find("div", class_=lambda c: c and "solution" in c)
    if sol_block:
        sol_ck = sol_block.find("div", class_=lambda c: c and "ck-content" in c) or sol_block

    # 2) SECOND PRIORITY → any <h2> containing Solution / Approach / Explanation
    if not sol_ck:
        h2_sol = None
        for h2 in soup.find_all("h2"):
            txt = h2.get_text(" ", strip=True).lower()
            if "solution" in txt or "explanation" in txt or "approach" in txt:
                h2_sol = h2
                break

        if h2_sol:
            sol_container = h2_sol.find_parent("div")
            sol_ck = sol_container.find("div", class_=lambda c: c and "ck-content" in c) or sol_container

    # 3) LAST FALLBACK → first ck-content after question section
    if not sol_ck:
        sol_ck = question_block.find_next("div", class_=lambda c: c and "ck-content" in c) or question_block

    # FINAL OUTPUT
    solution_text = sol_ck.get_text(" ", strip=True)
    solution_html = str(sol_ck)
    solution_images = _collect_images_with_parents(sol_ck, page_url)


    return {
        "question_number_text": question_number_text,
        "question_text": question_text,
        "question_html": question_html,
        "question_images": question_images,
        "hint_text": hint_text,
        "hint_html": hint_html,
        "hint_images": hint_images,
        "options": options,
        "correct_answer_text": correct_answer_text,
        "solution_text": solution_text,
        "solution_html": solution_html,
        "solution_images": solution_images,
    }


async def _scrape_single_solution(
    context,
    qid: int,
    solution_url: str,
    question_number_text: str,
    sem: asyncio.Semaphore,
    timeout: int = 30000,
) -> Dict:

    async with sem:
        page = await context.new_page()
        try:
            await delay(1.0, 3.0)
            resp = await page.goto(
                solution_url,
                timeout=timeout,
                wait_until="domcontentloaded",
            )
            if resp is None:
                logger.warning(
                    "Navigation to solution page returned None: %s",
                    solution_url,
                )

            try:
                await page.wait_for_selector(
                    "body",
                    timeout=8000,
                )
            except Exception:
                await page.wait_for_timeout(2500)

            # Use full page HTML so options + hint are visible
            rendered_html = await page.content()
            page_url = page.url  # for logging if needed

            structured = _parse_solution_page_structured(rendered_html, page_url)

            # Ensure we always have a meaningful question_number_text
            # qtext = structured.get("question_number_text") or ""
            # if not qtext.strip():
            #     structured["question_number_text"] = f"Question {qid}"

            # await delay(0.8, 2.0)

            # # Return ONLY the structured fields plus id
            # result: Dict = {"id": qid}
            # result.update(structured)
            # return result
            
            structured["question_number_text"] = question_number_text or f"Question {qid}"

            await delay(0.8, 2.0)

            result: Dict = {"id": qid}
            result.update(structured)
            return result

        except Exception as exc:
            logger.exception("Failed to scrape solution page %s: %s", solution_url, exc)
            # Minimal error object; no solution_link/solution_page/status
            return {
                "id": qid,
                "error": str(exc),
            }
        finally:
            try:
                await page.close()
            except Exception:
                pass



async def scrape_collegedunia_questions(context, page) -> List[Dict]:
    
    try:
        await page.wait_for_timeout(1500)
        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")

        container = soup.find(
            "div",
            class_=lambda x: x and TARGET_CONTAINER_CLASS in x,
        )
        if not container:
            container = soup.find(
                "div",
                class_=lambda x: x
                and "exam-page" in x
                and "listing-article-new-design-clg" in x,
            )

        if not container:
            logger.warning("Main container not found on page.")
            return []

        question_divs = container.find_all("div", class_="question")
        logger.info("Found %d question blocks", len(question_divs))

        # --------- First array: just URLs (internal only) ----------
        solution_urls: List[Dict] = []
        q_index = 0

        for qdiv in question_divs:
            q_index += 1
            
            ans_div = qdiv.find("div", class_="answer-section")
            _, solution_link = _extract_correct_answer_and_link(ans_div)
            
            raw_text = qdiv.get_text("\n", strip=True)
            first_line = raw_text.splitlines()[0].strip() if raw_text else ""
            
            if first_line.lower().startswith("question"):
                # e.g. "Question 7:" -> "Question 7"
                question_number_text = first_line.rstrip(":").strip()
            else:
                # safe fallback if structure changes
                question_number_text = f"Question {q_index}"
            

            solution_urls.append(
                {
                    "id": q_index,
                    "solution_link": solution_link or "",
                    "question_number_text": question_number_text,
                }
            )

        # --------- Second array: visit each solution URL ----------
        sem = asyncio.Semaphore(MAX_CONCURRENT_SOLUTIONS)
        tasks: List[asyncio.Task] = []

        for entry in solution_urls:
            qid = entry["id"]
            link = entry["solution_link"]
            qnum_text = entry["question_number_text"]
            if not link:
                continue
            tasks.append(
                asyncio.create_task(
                    _scrape_single_solution(context, qid, link, qnum_text, sem)
                )
            )

        solutions_detail: List[Dict] = []
        if tasks:
            logger.info(
                "Scraping %d solution pages with concurrency=%d",
                len(tasks),
                MAX_CONCURRENT_SOLUTIONS,
            )
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, Exception):
                    logger.error("Unexpected error in solution task: %s", res)
                    continue
                solutions_detail.append(res)

        await delay(0.4, 1.0)

        # Return ONLY array 2 (solutions_detail)
        return solutions_detail

    except Exception as exc:
        logger.exception("scrape_collegedunia_questions failed: %s", exc)
        return []
