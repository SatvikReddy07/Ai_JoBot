import logging
from typing import List
from datetime import datetime
import httpx
from .base import BaseConnector, RawJob, clean_html, parse_location, parse_employment_type

logger = logging.getLogger(__name__)

class GreenhouseConnector(BaseConnector):
    """
    Retrieves public job postings from Greenhouse API:
    https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true
    """

    BASE_URL = "https://boards-api.greenhouse.io/v1/boards"

    async def fetch_jobs(self) -> List[RawJob]:
        raw_jobs: List[RawJob] = []
        url = f"{self.BASE_URL}/{self.board_token}/jobs?content=true"

        headers = {
            "User-Agent": "HSE-Career-Agent/1.0",
            "Accept": "application/json"
        }

        try:
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 404:
                    logger.warning(f"Greenhouse board '{self.board_token}' not found (404).")
                    return []
                
                response.raise_for_status()
                data = response.json()
                
                jobs_list = data.get("jobs", [])
                for item in jobs_list:
                    job_id = str(item.get("id"))
                    title = item.get("title", "").strip()
                    loc_name = item.get("location", {}).get("name", "").strip() or "Unknown"
                    raw_html = item.get("content", "")
                    description = clean_html(raw_html)
                    job_url = item.get("absolute_url", "")
                    
                    # Parse location
                    city, country = parse_location(loc_name)
                    
                    # Also inspect description header for location if unknown
                    if country == "Unknown":
                        sample_head = description[:500]
                        _, detected_country = parse_location(sample_head)
                        if detected_country != "Unknown":
                            country = detected_country

                    # Parse employment type
                    emp_type, is_perm = parse_employment_type(f"{title} {description[:600]}")

                    # Date posted
                    posted_date = None
                    updated_at_str = item.get("updated_at")
                    if updated_at_str:
                        try:
                            posted_date = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
                        except Exception:
                            posted_date = None

                    raw_job = RawJob(
                        source="greenhouse",
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
            logger.error(f"HTTP error fetching Greenhouse board '{self.board_token}': {exc}")
            raise
        except Exception as exc:
            logger.error(f"Unexpected error fetching Greenhouse board '{self.board_token}': {exc}")
            raise

        return raw_jobs
