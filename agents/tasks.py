from crewai import Task
from agents.definitions import (
    research_agent,
    technology_agent,
    decision_maker_agent,
    opportunity_agent,
    email_agent,
    report_agent,
)


def build_tasks(company_name, website, report_date: str):

    website_note = (
        f"Use the Website Scraper tool to visit '{website}' and read its actual content."
        if website
        else (
            f"No website was provided. Search the web for '{company_name}' official site "
            "and public information. Clearly note when data comes from search vs. direct scrape."
        )
    )

    task_research = Task(
        description=(
            f"Research the company '{company_name}'. {website_note} "
            "Extract concrete, factual details — not generic filler. "
            "Include: what the company does, who they serve, business model, "
            "approximate company size (employees/revenue if public), headquarters, "
            "funding stage if startup, and 2-3 recent news items or product launches. "
            "Cite specific facts from the sources you find."
        ),
        expected_output=(
            "A detailed Markdown report with these exact sections:\n"
            "## Company Overview\n"
            "(3-4 sentences executive summary)\n\n"
            "## Products & Services\n"
            "(bullet list of specific offerings)\n\n"
            "## Industry & Market\n"
            "(industry, target customers, competitive positioning)\n\n"
            "## Company Size & Scale\n"
            "(employees, revenue, locations — state 'Not publicly available' if unknown)\n\n"
            "## Recent News & Developments\n"
            "(2-3 bullet points with dates where possible)"
        ),
        agent=research_agent,
    )

    task_technology = Task(
        description=(
            f"Analyze the technology stack for '{company_name}'. "
            + (f"Run the Technology Stack Detector on '{website}'. " if website else "")
            + "Cross-reference detected signals with the company research. "
            "Categorize every technology found. Note integration opportunities "
            "(e.g. if they use HubSpot, Salesforce, AWS, etc.)."
        ),
        expected_output=(
            "Start with a brief 2-sentence tech summary, then provide a JSON block:\n"
            "```json\n"
            '{"frontend": [], "backend": [], "cloud": [], "databases": [], "third_party_apis": []}\n'
            "```\n"
            "Follow with a Markdown section '## Technology Stack' listing each category "
            "with bullet points. Only include technologies you have evidence for."
        ),
        agent=technology_agent,
        context=[task_research],
    )

    task_decision_makers = Task(
        description=(
            f"Find real, current decision makers at '{company_name}' who would buy software/AI solutions. "
            f"Search: '{company_name} CEO', '{company_name} CTO', '{company_name} VP Engineering', "
            f"'{company_name} Head of Product', '{company_name} leadership team'. "
            "Prioritize: CEO, CTO, VP Engineering, Head of Product, CRO. "
            "Only include people confirmed in search results — NEVER invent names. "
            "For each person: full name, exact title, LinkedIn URL, public email if available, "
            "and one sentence on why they are relevant to a software sales conversation."
        ),
        expected_output=(
            "A Markdown section '## Key Decision Makers' with a table:\n"
            "| Name | Title | LinkedIn | Email | Relevance |\n"
            "|------|-------|----------|-------|----------|\n"
            "Include 3-5 real people. If fewer than 3 found, explain why and list what you did find."
        ),
        agent=decision_maker_agent,
        context=[task_research],
    )

    task_opportunities = Task(
        description=(
            f"Identify exactly 3 high-value software/AI sales opportunities for '{company_name}'. "
            "Each opportunity MUST reference specific technologies detected and specific company facts. "
            "Search for recent challenges, hiring patterns, or growth signals if needed. "
            "Make opportunities actionable for a B2B software salesperson — not generic advice."
        ),
        expected_output=(
            "A Markdown section '## Business Opportunities' with exactly 3 opportunities.\n"
            "Use this format for EACH:\n\n"
            "### Opportunity 1: [Short Title]\n"
            "**Pain Point:** [Specific problem tied to their tech/business]\n"
            "**Proposed Solution:** [Concrete software/AI solution you would sell]\n"
            "**Business Impact:** [Quantified ROI, time saved, or revenue impact]\n\n"
            "Repeat for Opportunities 2 and 3."
        ),
        agent=opportunity_agent,
        context=[task_research, task_technology],
    )

    task_email = Task(
        description=(
            f"Write a personalized cold-outreach email for '{company_name}'. "
            "Target the most relevant decision maker found. "
            "Reference ONE specific company fact, ONE detected technology, "
            "and ONE opportunity as the value proposition. "
            "Tone: professional, concise, peer-to-peer (not salesy). "
            "Include a low-friction CTA (15-min call, not 'buy now'). "
            "Maximum 180 words in the body."
        ),
        expected_output=(
            "A Markdown section '## Outreach Email' containing:\n"
            "**Subject:** [Compelling, specific subject line]\n\n"
            "[Full email with greeting, 2-3 short paragraphs, sign-off]\n"
            "Do not use placeholder brackets like [Name] — use actual names found."
        ),
        agent=email_agent,
        context=[task_research, task_decision_makers, task_opportunities],
    )

    task_report = Task(
        description=(
            f"Compile ALL research for '{company_name}' into one polished executive report. "
            f"Use report date: {report_date}. "
            "Preserve all detail from prior tasks — do not summarize away specifics. "
            "Ensure consistent Markdown headings so sections parse correctly."
        ),
        expected_output=(
            f"# Sales Lead Research Report: {company_name}\n"
            f"**Report Date:** {report_date}\n"
            f"**Prepared by:** AI Sales Lead Research Agent\n\n"
            "Include ALL sections in order:\n"
            "1. Company Overview (full detail from research)\n"
            "2. Technology Stack (JSON + categorized list)\n"
            "3. Key Decision Makers (full table)\n"
            "4. Business Opportunities (all 3 with Pain/Solution/Impact)\n"
            "5. Outreach Email (subject + full body)\n\n"
            "Do not add commentary — only compile existing findings."
        ),
        agent=report_agent,
        context=[
            task_research,
            task_technology,
            task_decision_makers,
            task_opportunities,
            task_email,
        ],
    )

    return [
        task_research,
        task_technology,
        task_decision_makers,
        task_opportunities,
        task_email,
        task_report,
    ]
