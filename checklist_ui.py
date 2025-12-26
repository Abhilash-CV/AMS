import streamlit as st
import pandas as pd

def checklist_ui(year, program):
    st.header("📘 Admission Process – Master Verification Checklist")
    st.caption(f"Academic Year: {year} | Program: {program}")
    st.info("Static read-only checklist. For reference / audit / committee use only.")

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

    # ------------------------------------------------ APPLICATION
    with tabs[0]:
        st.subheader("Application")

        data = [
            ("Prospectus Upload", "Prospectus uploaded and accessible"),
            ("Academic Year Configuration", "Correct academic year configured"),
            ("Age Limit Configuration", "Age limits set as per prospectus"),
            ("Certificate Format Configuration", "Certificate formats match prospectus"),
            ("Help Documentation", "How to Apply, Fee Payment, Image Upload, Prerequisites available"),
            ("Contact Information", "Helpdesk / contact number displayed"),
            ("Forgot Application Number", "Retrieval functionality working"),
            ("Forgot Password", "Password reset working correctly"),
            ("OTP Verification", "OTP generation and validation working"),
            ("New Application Creation", "Application creation working (Local & Live)"),
            ("Field Validation", "Mandatory and optional field validation enforced"),
            ("Save Draft / Resume", "Draft save and resume functionality working"),
            ("Final Submission", "Submission successful without errors"),
            ("Application Fee – General", "Fee configured correctly"),
            ("Application Fee – SC/ST", "Fee configured correctly"),
            ("Payment Gateway", "Payment gateway integrated and functional"),
            ("Payment Handling", "Success / failure handling correct"),
            ("Live Photo Capture", "Live photo capture working"),
            ("Image Upload Validation", "Size, format, clarity validated"),
            ("Document Upload", "Certificates uploaded correctly")
        ]
        st.dataframe(pd.DataFrame(data, columns=["Checklist Item", "Description"]), hide_index=True)

    # ------------------------------------------------ ANSWER KEY
    with tabs[1]:
        st.subheader("Answer Key")

        data = [
            ("Provisional Answer Key", "Generated via authorized CDIT application"),
            ("Question Coverage", "All questions included"),
            ("Answer Coverage", "Answers provided for all questions"),
            ("Accuracy Verification", "Question numbers, options and answers verified"),
            ("Publication", "Provisional answer key published"),
            ("SMS Notification", "SMS sent to all appeared candidates"),
            ("Challenge Menu", "Answer key challenge menu enabled"),
            ("Challenge Recording", "Challenges received and logged"),
            ("Expert Review", "Expert committee review completed"),
            ("Committee Approval", "Expert committee opinion documented"),
            ("Answer Key Revision", "Deletion / option changes applied"),
            ("Final Publication", "Final answer key published"),
            ("Version Control", "Provisional & final versions archived"),
            ("Final SMS", "SMS sent after final publication")
        ]
        st.dataframe(pd.DataFrame(data, columns=["Checklist Item", "Description"]), hide_index=True)

    # ------------------------------------------------ RANK LIST
    with tabs[2]:
        st.subheader("Rank List")

        data = [
            ("Tie-Break Conditions", "Tie-break rules applied consistently"),
            ("DOB Rule", "If DOB missing, treat as present date"),
            ("Answer Key Changes", "Deletion / option changes reflected in marks"),
            ("Qualification Criteria", "Eligibility criteria applied correctly"),
            ("Withheld Conditions", "Withheld rules applied"),
            ("Provisionally Included", "Provisionally included candidates flagged"),
            ("Total Count", "Total candidates count verified"),
            ("Withheld Count", "Withheld count matches detailed list"),
            ("Font Usage", "Approved font and size used"),
            ("Page Numbering", "Page No. format verified"),
            ("Remarks", "Remarks added where applicable"),
            ("SMS", "SMS sent to all candidates"),
            ("WPC", "Handled if any")
        ]
        st.dataframe(pd.DataFrame(data, columns=["Checklist Item", "Description"]), hide_index=True)

    # ------------------------------------------------ CATEGORY LIST
    with tabs[3]:
        st.subheader("Category List")

        data = [
            ("Online vs Scrutiny", "Online category matched with scrutiny"),
            ("Withheld Marking", "Withheld candidates marked (Memo Status = S)"),
            ("DOB Verification", "DOB cross-checked"),
            ("Nationality", "Nationality cross-checked"),
            ("Nativity", "Nativity cross-checked"),
            ("Category Count (Scrutiny)", "Category-wise scrutiny count verified"),
            ("Category Count (Online)", "Category-wise online count verified"),
            ("KIRTADS", "Provisionally included if not accepted"),
            ("Provisionally Included", "Marked correctly"),
            ("Category Labels", "As per prospectus"),
            ("OE / PD / XS", "Included where applicable"),
            ("Special Reservation", "XP, FM, CC, DK, HR, RP, SD, LG verified"),
            ("Qualified Candidates", "Only qualified candidates included"),
            ("PD Eligibility", "Eligible courses mentioned"),
            ("SMS", "SMS sent to Online + Scrutiny candidates"),
            ("WPC", "Handled if any")
        ]
        st.dataframe(pd.DataFrame(data, columns=["Checklist Item", "Description"]), hide_index=True)

    # ------------------------------------------------ INTER-SE MERIT
    with tabs[4]:
        st.subheader("Inter-Se Merit")

        data = [
            ("Sports Council List", "Prepared strictly as per approved list"),
            ("Eligible Candidates", "Only eligible candidates included"),
            ("PI / PT Lists", "Generated correctly"),
            ("PI / PT Count", "Counts verified"),
            ("SMS", "Sent to eligible candidates only"),
            ("Font & Page No.", "Verified"),
            ("Remarks", "Added if any"),
            ("WPC", "Handled if any")
        ]
        st.dataframe(pd.DataFrame(data, columns=["Checklist Item", "Description"]), hide_index=True)

    # ------------------------------------------------ SERVICE QUOTA
    with tabs[5]:
        st.subheader("Service Quota")

        data = [
            ("SQ List", "Received from DME / HSE / IMS"),
            ("Online Claim Count", "Matched with official list"),
            ("Eligibility", "Eligibility conditions verified"),
            ("Qualification Criteria", "Applied correctly"),
            ("Font & Page No.", "Verified"),
            ("SMS", "Sent as per official list"),
            ("Final SMS", "Sent after approval"),
            ("WPC", "Handled if any")
        ]
        st.dataframe(pd.DataFrame(data, columns=["Checklist Item", "Description"]), hide_index=True)

    # ------------------------------------------------ OPTION REGISTRATION
    with tabs[6]:
        st.subheader("Option Registration")

        data = [
            ("Option Fee", "Configured as per prospectus"),
            ("Fee Exemption", "SC/ST exemption applied"),
            ("College & Course Master", "Verified"),
            ("Option Count", "Total options counted correctly"),
            ("Govt / Self / NRI / Minority", "Counts verified"),
            ("Tuition Fee", "Verified for all categories"),
            ("Option List Download", "Format verified"),
            ("Memo Clearance", "Nativity & nationality clearance open"),
            ("SMS", "Sent as per phase")
        ]
        st.dataframe(pd.DataFrame(data, columns=["Checklist Item", "Description"]), hide_index=True)

    # ------------------------------------------------ SEAT MATRIX
    with tabs[7]:
        st.subheader("Seat Matrix")

        data = [
            ("Course Code", "Verified"),
            ("College Code", "Verified"),
            ("Category Code", "As per prospectus"),
            ("Seat Breakup", "Total vs breakup tally"),
            ("Reservation Rules", "Satisfied"),
            ("New Seats", "Incorporated")
        ]
        st.dataframe(pd.DataFrame(data, columns=["Checklist Item", "Description"]), hide_index=True)

    # ------------------------------------------------ ALLOTMENT
    with tabs[8]:
        st.subheader("Allotment")

        data = [
            ("Qualified Candidates", "Only eligible candidates considered"),
            ("Withheld / Ineligible", "Excluded"),
            ("Option Count", "Verified"),
            ("Seat Count", "Verified"),
            ("Vacant Seats", "Verified"),
            ("Rank Protection", "Ensured"),
            ("Conversion Rules", "Applied"),
            ("SMS", "Sent")
        ]
        st.dataframe(pd.DataFrame(data, columns=["Checklist Item", "Description"]), hide_index=True)

    # ------------------------------------------------ LAST RANK
    with tabs[9]:
        st.subheader("Last Rank")

        data = [
            ("List Title", "Correctly mentioned"),
            ("Category Codes", "As per prospectus"),
            ("Excluded Categories", "Not listed"),
            ("Alignment", "Aligned with allotment"),
            ("Final Publication", "After issue resolution")
        ]
        st.dataframe(pd.DataFrame(data, columns=["Checklist Item", "Description"]), hide_index=True)

    # ------------------------------------------------ ALLOTMENT MEMO
    with tabs[10]:
        st.subheader("Allotment Memo")

        data = [
            ("Academic Year", "Correctly mentioned"),
            ("Tuition Fee", "Correct for all categories"),
            ("Fee Exemption", "Applied"),
            ("Date of Joining", "Mentioned correctly"),
            ("Internal Change", "No joining date"),
            ("Documents", "Listed as per prospectus"),
            ("KIRTADS", "Indicated"),
            ("Footnotes", "Added if required")
        ]
        st.dataframe(pd.DataFrame(data, columns=["Checklist Item", "Description"]), hide_index=True)

    # ------------------------------------------------ VACANT SEATS
    with tabs[11]:
        st.subheader("Vacant Seats")

        data = [
            ("Unallotted Seats", "Verified"),
            ("Non-Joining Seats", "Verified"),
            ("TC Seats", "Verified"),
            ("Newly Added Seats", "Included in calculation")
        ]
        st.dataframe(pd.DataFrame(data, columns=["Checklist Item", "Description"]), hide_index=True)
