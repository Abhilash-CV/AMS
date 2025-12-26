import streamlit as st
import pandas as pd

def checklist_ui(year, program):
    st.header("📘 Admission Process – Master Verification Checklist")
    st.caption(f"Academic Year: {year} | Program: {program}")
    st.info("Static reference checklist. Read-only.")

    tabs = st.tabs([
        "Application",
        "Answer Key",
        "Rank List",
        "Category List",
        "Inter-Se Merit",
        "Service Quota",
        "Option Registration",
        "Seat Matrix",
        "Allotment",
        "Last Rank",
        "Allotment Memo",
        "Vacant Seats"
    ])

    def show(data):
        st.dataframe(
            pd.DataFrame(data, columns=["Checklist Item", "Description"]),
            hide_index=True,
            use_container_width=True
        )

    # ---------------- Application
    with tabs[0]:
        show([
            ("Prospectus Upload", "Prospectus uploaded and accessible"),
            ("Academic Year", "Correct academic year configured"),
            ("Age Limit", "As per prospectus"),
            ("Certificate Format", "Matches prospectus"),
            ("Help Docs", "How to Apply / Fee / Image Upload"),
            ("Contact", "Helpdesk displayed"),
            ("Forgot App No", "Working"),
            ("Forgot Password", "Working"),
            ("OTP", "Generated and validated"),
            ("Application Creation", "Local & Live"),
            ("Field Validation", "Mandatory & optional"),
            ("Save Draft", "Working"),
            ("Final Submission", "No errors"),
            ("Fee – General", "Configured"),
            ("Fee – SC/ST", "Configured"),
            ("Payment Gateway", "Integrated"),
            ("Payment Handling", "Success / Failure handled"),
            ("Live Photo", "Working"),
            ("Image Validation", "Size / Format / Clarity"),
            ("Document Upload", "Certificates uploaded")
        ])

    # ---------------- Answer Key
    with tabs[1]:
        show([
            ("Provisional Key", "Generated via CDIT"),
            ("Question Coverage", "All questions included"),
            ("Answer Coverage", "All answers provided"),
            ("Accuracy", "Verified"),
            ("Publication", "Published"),
            ("SMS", "Sent to appeared candidates"),
            ("Challenge Menu", "Enabled"),
            ("Challenge Recording", "Logged"),
            ("Expert Review", "Completed"),
            ("Committee Approval", "Documented"),
            ("Revision", "Deletion / Option change"),
            ("Final Key", "Published"),
            ("Version Control", "Archived"),
            ("Final SMS", "Sent")
        ])

    # ---------------- Rank List
    with tabs[2]:
        show([
            ("Tie Break", "Applied correctly"),
            ("DOB Rule", "Missing DOB → Present date"),
            ("Answer Key Changes", "Reflected"),
            ("Qualification", "Applied"),
            ("Withheld", "Applied"),
            ("Provisional", "Flagged"),
            ("Total Count", "Verified"),
            ("Withheld Count", "Verified"),
            ("Font", "Approved"),
            ("Page No", "X/Y"),
            ("Remarks", "Added"),
            ("SMS", "Sent"),
            ("WPC", "Handled")
        ])

    # ---------------- Category List
    with tabs[3]:
        show([
            ("Online vs Scrutiny", "Matched"),
            ("Withheld Mark", "Memo Status = S"),
            ("DOB", "Verified"),
            ("Nationality", "Verified"),
            ("Nativity", "Verified"),
            ("Scrutiny Count", "Verified"),
            ("Online Count", "Verified"),
            ("KIRTADS", "Provisionally included"),
            ("Provisionally Included", "Marked"),
            ("Category Labels", "As per prospectus"),
            ("OE / PD / XS", "Included"),
            ("Special Reservation", "XP, FM, CC, DK, HR, RP, SD, LG"),
            ("Qualified Only", "Yes"),
            ("PD Eligibility", "Mentioned"),
            ("SMS", "Sent"),
            ("WPC", "Handled")
        ])

    # ---------------- Inter-Se Merit
    with tabs[4]:
        show([
            ("Sports Council List", "Approved"),
            ("Eligibility", "Verified"),
            ("PI/PT Lists", "Generated"),
            ("PI/PT Count", "Verified"),
            ("SMS", "Sent"),
            ("Font/Page No", "Verified"),
            ("Remarks", "Added"),
            ("WPC", "Handled")
        ])

    # ---------------- Service Quota
    with tabs[5]:
        show([
            ("SQ List", "From DME/HSE/IMS"),
            ("Online Claim", "Matched"),
            ("Eligibility", "Verified"),
            ("Qualification", "Applied"),
            ("Font/Page No", "Verified"),
            ("SMS", "Sent"),
            ("Final SMS", "Sent"),
            ("WPC", "Handled")
        ])

    # ---------------- Option Registration
    with tabs[6]:
        show([
            ("Option Fee", "As per prospectus"),
            ("Fee Exemption", "SC/ST"),
            ("College/Course Master", "Verified"),
            ("Option Count", "Verified"),
            ("Govt/Self/NRI/Minority", "Verified"),
            ("Tuition Fee", "Verified"),
            ("Option Download", "Format verified"),
            ("Memo Clearance", "Enabled"),
            ("SMS", "Sent")
        ])

    # ---------------- Seat Matrix
    with tabs[7]:
        show([
            ("Course Code", "Verified"),
            ("College Code", "Verified"),
            ("Category Code", "Verified"),
            ("Seat Breakup", "Tallied"),
            ("Reservation", "Satisfied"),
            ("New Seats", "Included")
        ])

    # ---------------- Allotment
    with tabs[8]:
        show([
            ("Qualified Only", "Yes"),
            ("Withheld/Ineligible", "Excluded"),
            ("Option Count", "Verified"),
            ("Seat Count", "Verified"),
            ("Vacant Seats", "Verified"),
            ("Rank Protection", "Ensured"),
            ("Conversion", "Applied"),
            ("SMS", "Sent")
        ])

    # ---------------- Last Rank
    with tabs[9]:
        show([
            ("List Title", "Correct"),
            ("Category Code", "As per prospectus"),
            ("Excluded Categories", "Not listed"),
            ("Alignment", "With allotment"),
            ("Final Publish", "After resolution")
        ])

    # ---------------- Allotment Memo
    with tabs[10]:
        show([
            ("Academic Year", "Correct"),
            ("Tuition Fee", "All categories"),
            ("Exemption", "Applied"),
            ("Joining Date", "Correct"),
            ("Internal Change", "No joining date"),
            ("Documents", "As per prospectus"),
            ("KIRTADS", "Indicated"),
            ("Footnotes", "Added")
        ])

    # ---------------- Vacant Seats
    with tabs[11]:
        show([
            ("Unallotted Seats", "Verified"),
            ("Non-Joining", "Verified"),
            ("TC Seats", "Verified"),
            ("New Seats", "Included")
        ])
