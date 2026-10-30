# Regulatory source register

The application uses retrieval as evidence collection only. A PDF's presence in this folder does not prove that it is the currently effective document for a particular parcel or authority.

| ID | Authority | Document | Official URL | Local file/status |
|---|---|---|---|---|
| SRC-001 | Bruhat Bengaluru Mahanagara Palike (BBMP) | Bangalore Mahanagara Palike Building Bye-Laws, 2003 | https://site.bbmp.gov.in/PDF/townplanning/Bangalore-Building-Byelaws-%202003.pdf | data/bye_laws/Bangalore-Building-Byelaws.pdf; local historical corpus. Not confirmed as current consolidated version. |
| SRC-002 | BBMP / Bangalore Development Authority | Revised Master Plan 2015 Zoning Regulations | https://site.bbmp.gov.in/documents/Zoning_Regulations_RMP2015f.pdf | Not included in local corpus. Required for zoning, use, FAR, height, and related provisions. |
| SRC-003 | Government of Karnataka, Urban Development Department | Subsequent amendments to RMP-2015, including 2025/2026 amendment sequence | https://site.bbmp.gov.in/townplanning.html | Local project has not ingested a final consolidated amendment set. A Gazette dated 17 October 2026 was identified during review; obtain and verify the official Gazette copy and subsequent orders before current-rule decisions. |

Review date: 29 October 2026.

The older source register described the local PDF as the Karnataka Municipal Corporations Model Building Bye-Laws 2017 and listed a different filename. That was incorrect. The local file identifies itself as Bangalore Building Bye-Laws 2003. The app therefore records currentness as unchecked and routes all outputs to specialist review.

Before expanding the corpus:

1. Download official zoning regulations and final amendments from the authority/Gazette.
2. Record notification number, publication date, effective date, official URL, and SHA-256.
3. Check for later amendments, stays, and parcel-specific planning-district maps with the competent authority.
4. Obtain qualified review of extracted tables and test values.
5. Re-run the narrow-plot/narrow-road case against the consolidated corpus.

No substantive rule value should be treated as legally current until these steps are complete.
