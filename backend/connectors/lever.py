import logging
from typing import List
from datetime import datetime, timezone
import httpx
from .base import BaseConnector, RawJob, clean_html, parse_location, parse_employment_type, validate_feed_items

logger = logging.getLogger(__name__)

class LeverConnector(BaseConnector):
    """
    Retrieves public job postings from Lever API:
    https://api.lever.co/v0/postings/{board_token}?mode=json
    """

    BASE_URL = "https://api.lever.co/v0/postings"

    async def fetch_jobs(self) -> List[RawJob]:
        raw_jobs: List[RawJob] = []
        url = f"{self.BASE_URL}/{self.board_token}?mode=json"

        headers = {
            "User-Agent": "HSE-Career-Agent/1.0",
            "Accept": "application/json"
        }

        try:
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                response = await client.get(url, headers=headers)
                
                response.raise_for_status()
                postings = response.json()

                # Either official hostedUrl or applyUrl is accepted, but malformed
                # responses must never become an apparently empty snapshot.
                if isinstance(postings, list):
                    postings = [{**item, "hostedUrl": item.get("hostedUrl") or item.get("applyUrl")} if isinstance(item, dict) else item for item in postings]
                postings = validate_feed_items(postings, "text", "hostedUrl")

                for item in postings:
                    job_id = str(item.get("id"))
                    title = item.get("text", "").strip()
                    
                    categories = item.get("categories", {})
                    loc_name = categories.get("location", "").strip() or "Unknown"
                    commitment = categories.get("commitment", "")
                    
                    raw_html = item.get("description", "")
                    description = item.get("descriptionPlain")
                    if not description:
                        description = clean_html(raw_html)

                    # Also append additional lists (requirements, responsibilities) if present
                    lists = item.get("lists", [])
                    if lists and isinstance(lists, list):
                        extra_parts = []
                        for sub_list in lists:
                            sub_text = sub_list.get("text", "")
                            sub_content = clean_html(sub_list.get("content", ""))
                            extra_parts.append(f"\n{sub_text}:\n{sub_content}")
                        description += "\n" + "\n".join(extra_parts)

                    job_url = item.get("hostedUrl") or item.get("applyUrl", "")

                    # Location
                    city, country = parse_location(loc_name)
                    if country == "Unknown":
                        sample_head = description[:500]
                        _, detected_country = parse_location(sample_head)
                        if detected_country != "Unknown":
                            country = detected_country

                    # Employment type
                    emp_sample = f"{commitment} {title} {description[:400]}"
                    emp_type, is_perm = parse_employment_type(emp_sample)

                    # Date posted
                    posted_date = None
                    created_at_ms = item.get("createdAt")
                    if created_at_ms:
                        try:
                            posted_date = datetime.fromtimestamp(created_at_ms / 1000.0, tz=timezone.utc)
                        except Exception:
                            posted_date = None

                    raw_job = RawJob(
                        source="lever",
                        source_job_id=job_id,
                        company=self.company_name,
                        title=title,
                        location=loc_name,
                        city=city,
                        country=country,
                        employment_type=emp_type,
                        is_permanent_fulltime=is_perm,
                        description=description,
                        raw_description_html=raw_html,
                        url=job_url,
                        posted_date=posted_date
                    )
                    raw_jobs.append(raw_job)

        except httpx.HTTPError as exc:
            logger.error(f"HTTP error fetching Lever board '{self.board_token}': {exc}")
            raise
        except Exception as exc:
            logger.error(f"Unexpected error fetching Lever board '{self.board_token}': {exc}")
            raise

        return raw_jobs
