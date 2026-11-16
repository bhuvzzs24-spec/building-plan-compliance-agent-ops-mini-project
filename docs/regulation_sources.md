# Regulatory source register

The application uses retrieval as evidence collection only. A PDF's presence in this folder does not prove that it is the currently effective document for a particular parcel or authority.

| ID | Authority | Document | Official URL | Local file/status |
|---|---|---|---|---|
| SRC-001 | Bruhat Bengaluru Mahanagara Palike (BBMP) | Bangalore Mahanagara Palike Building Bye-Laws, 2003 | https://site.bbmp.gov.in/PDF/townplanning/Bangalore-Building-Byelaws-%202003.pdf | data/bye_laws/Bangalore-Building-Byelaws.pdf; local historical corpus. Not confirmed as current consolidated version. |
| SRC-002 | Bangalore Development Authority (document owner); BBMP Town Planning (official publication portal) | Revised Master Plan 2015, Volume III: Zoning of Landuse and Regulations. Cover states approved by Government under G.O. UDD 540 BEM AA SE 2004 dated 22 June 2007 as part of RMP 2015. | https://site.bbmp.gov.in/PDF/townplanning/Zoning_Regulations_RMP2015f%20%281%29.pdf | Official PDF URL verified 16 Nov 2026. Local acquisition timed out; not indexed. Applicability described in document as Bangalore Metropolitan Area/Local Planning Area and dependent on planning-district maps. SHA-256 not recorded because no local copy. Current effectiveness not established. |
| SRC-003 | BBMP Town Planning / Government of Karnataka | Zoning regulation amendments and later RMP-related notices | https://site.bbmp.gov.in/zrammendements.html and https://site.bbmp.gov.in/townplanning.html | Official amendment directory identified; page access timed out during this review. Individual notification numbers, effective dates, supersession status, and consolidated applicability have not been verified or ingested. |

Review date: 16 November 2026. Source-page discovery used the BBMP Town Planning portal; an official RMP-2015 PDF was retrievable via web search, while direct local download and the amendment-page fetch timed out. This register is not a legal-currentness finding.

The older source register described the local PDF as the Karnataka Municipal Corporations Model Building Bye-Laws 2017 and listed a different filename. That was incorrect. The local file identifies itself as Bangalore Building Bye-Laws 2003. The app therefore records currentness as unchecked and routes all outputs to specialist review.

Before expanding the active corpus:

1. Download the official zoning PDF and individual final amendments from the BBMP/BDA source pages (the direct zoning PDF download did not complete in this environment).
2. Record notification number, publication date, effective date, official URL, and SHA-256.
3. Check for later amendments, stays, and parcel-specific planning-district maps with the competent authority.
4. Obtain qualified review of extracted tables and test values.
5. Re-run the narrow-plot/narrow-road case against the consolidated corpus.

No substantive rule value should be treated as legally current until these steps are complete.
