import os

from .outreach import (
    load_recent_leads,
    prepare_lead_for_outreach,
    save_lead_log,
    send_lead_outreach,
)
from .scraper import select_random_businesses


def process_and_send(leads):
    prepared = [prepare_lead_for_outreach(lead) for lead in leads]
    outreach_candidates = [
        lead for lead in prepared
        if not lead.get("has_website")
        and (lead.get("email") or lead.get("phone"))
        and lead.get("outreach_opt_in") is True
    ]

    print(f"Found {len(leads)} scraped leads; {len(outreach_candidates)} opted-in leads ready for outreach.")

    for lead in outreach_candidates:
        print(f"\nBusiness: {lead.get('name')}")
        print(f"Category: {lead.get('category')}")
        print(f"Address: {lead.get('address')}")
        print(f"Website: {lead.get('website') or 'NULL'}")
        print(f"Message: {lead.get('message')[:180]}...")
        send_lead_outreach(lead)

    not_consented = sum(
        1 for lead in prepared
        if not lead.get("has_website") and not lead.get("outreach_opt_in")
    )
    if not_consented:
        print(f"Skipped {not_consented} leads without recorded outreach opt-in; messages remain unsent.")

    output_path = save_lead_log(prepared)
    print(f"\nLead report saved to: {output_path}")
    return prepared


def main() -> None:
    fresh_leads = select_random_businesses(per_category=5)

    if fresh_leads:
        print("Maps search produced fresh leads. Sending those first.")
        process_and_send(fresh_leads)
    else:
        recent_leads = load_recent_leads()
        if recent_leads:
            print("Google Maps did not return fresh results. Sending cached leads from outreach.json instead.")
            process_and_send(recent_leads)
        else:
            print("No fresh leads and no cached outreach file found. Nothing sent.")

    print("Retrying Google Maps in a second pass to refresh the lead list.")
    retry_leads = select_random_businesses(per_category=5)
    if retry_leads:
        process_and_send(retry_leads)
    else:
        cached = load_recent_leads()
        if cached:
            print("Retry still blocked; sending the cached leads one more time.")
            process_and_send(cached)
        else:
            print("Retry still found no leads. Workflow ends here.")


if __name__ == "__main__":
    main()
