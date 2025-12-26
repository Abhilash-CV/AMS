import streamlit as st

def checklist_ui(year, program):
    st.header("📘 Admission Process – Master Verification Checklist")
    st.caption(f"Academic Year: {year} | Program: {program}")
    st.info("Static reference view. No inputs or edits allowed.")

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

    # -------------------- TAB 1 : APPLICATION --------------------
    with tabs[0]:
        st.subheader("Application")

        st.markdown("### Application Setup")
        st.markdown("""
- Prospectus uploaded and accessible  
- Correct academic year configured  
- Age limits set as per prospectus  
- Certificate formats match prospectus  
""")

        st.markdown("### Applicant Support")
        st.markdown("""
- How to Apply documentation available  
- Fee payment instructions available  
- Image upload instructions available  
- Eligibility / prerequisites displayed  
- Helpdesk / contact number displayed  
""")

        st.markdown("### Access & Recovery")
        st.markdown("""
- Forgot Application Number retrieval working  
- Forgot Password reset working  
- OTP generation and validation working  
""")

        st.markdown("### Application Creation")
        st.markdown("""
- New application creation working (Local & Live)  
- Mandatory and optional field validation  
- All menus and buttons functioning  
- Save draft and resume working  
""")

        st.markdown("### Application Submission")
        st.markdown("""
- Final submission successful without errors  
""")

        st.markdown("### Fee Management")
        st.markdown("""
- Application fee – General configured  
- Application fee – SC/ST configured  
- Payment gateway functional  
- Payment success / failure handling correct  
""")

        st.markdown("### Photo & Documents")
        st.markdown("""
- Live photo capture working  
- Image size / format / clarity validated  
- Document upload verified  
""")

    # -------------------- TAB 2 : ANSWER KEY --------------------
    with tabs[1]:
        st.subheader("Answer Key")

        st.markdown("### Provisional")
        st.markdown("""
- Generated via authorized CDIT application  
- All questions included  
- All answers provided  
- Accuracy verified  
- Published successfully  
- SMS sent to appeared candidates  
""")

        st.markdown("### Final")
        st.markdown("""
- Challenge menu enabled  
- Challenges recorded  
- Expert committee review completed  
- Committee approval documented  
- Deletion / option change applied  
- Final answer key published  
- Provisional & final versions archived  
- Final SMS sent  
""")

    # -------------------- TAB 3 : RANK LIST --------------------
    with tabs[2]:
        st.subheader("Rank List")

        st.markdown("### Merit Logic")
        st.markdown("""
- Tie-break rules applied correctly  
- DOB rule applied (Missing DOB → Present Date)  
- Answer key changes reflected in marks  
""")

        st.markdown("### Eligibility")
        st.markdown("""
- Qualification criteria applied  
- Withheld conditions applied  
- Provisionally included candidates flagged  
""")

        st.markdown("### Statistics")
        st.markdown("""
- Total candidate count verified  
- Withheld count verified  
- Provisionally included count verified  
""")

        st.markdown("### Documentation & Communication")
        st.markdown("""
- Footnotes added  
- Approved font & size used  
- Page numbering verified (X/Y)  
- Remarks added where applicable  
- SMS sent  
- WPC handled if any  
""")

    # -------------------- TAB 4 : CATEGORY LIST --------------------
    with tabs[3]:
        st.subheader("Category List")

        st.markdown("### Provisional")
        st.markdown("""
- Online vs scrutiny category matched  
- Withheld candidates marked (Memo Status = S)  
- DOB / Nationality / Nativity verified  
- Category-wise counts verified  
- NC / Photo / Signature verified  
- KIRTADS provisionally included  
- Provisionally included candidates marked  
- Category labels as per prospectus  
- OE / PD / XS included  
- Special reservations verified (XP, FM, CC, DK, HR, RP, SD, LG)  
- Only qualified candidates included  
- PD course eligibility mentioned  
- SMS sent  
- WPC handled if any  
""")

        st.markdown("### Final")
        st.markdown("""
- All issues resolved before publication  
- Final category-wise totals verified  
- Only qualified candidates included  
- PD course eligibility mentioned  
- SMS sent  
- WPC handled if any  
""")

    # -------------------- TAB 5 : INTER-SE MERIT --------------------
    with tabs[4]:
        st.subheader("Inter-Se Merit")

        st.markdown("""
- Sports Council approved list used  
- Only eligible candidates included  
- PI & PT lists generated  
- PI & PT counts verified  
- SMS sent to eligible candidates only  
- Footnotes / font / page numbering verified  
- Remarks added if any  
- WPC / court cases handled  
""")

    # -------------------- TAB 6 : SERVICE QUOTA --------------------
    with tabs[5]:
        st.subheader("Service Quota")

        st.markdown("""
- Official SQ list received (DME / HSE / IMS)  
- Online claim count matched  
- Eligibility verified  
- Qualification criteria applied  
- Footnotes / font / page numbering verified  
- SMS sent (provisional & final)  
- WPC / court cases handled  
""")

    # -------------------- TAB 7 : OPTION REGISTRATION --------------------
    with tabs[6]:
        st.subheader("Option Registration")

        st.markdown("""
- First phase fee & exemption verified  
- College & course master verified  
- All option counts verified  
- Tuition fee verified (Govt / Self / Mgmt / NRI / Minority)  
- Option list download format verified  
- Memo clearance enabled  
- Second & third phase logic verified  
- Stray phase restrictions applied  
- SMS sent as per phase  
""")

    # -------------------- TAB 8 : SEAT MATRIX --------------------
    with tabs[7]:
        st.subheader("Seat Matrix")

        st.markdown("""
- Course codes verified  
- College codes verified  
- Category codes verified  
- Seat breakup tally verified  
- Reservation rules satisfied  
- Newly added seats incorporated  
""")

    # -------------------- TAB 9 : ALLOTMENT --------------------
    with tabs[8]:
        st.subheader("Allotment")

        st.markdown("""
- Qualified candidates only  
- Withheld / ineligible excluded  
- Option count verified  
- Seat count verified  
- Vacant seats verified  
- Rank protection ensured  
- Conversion rules applied  
- SMS sent  
""")

    # -------------------- TAB 10 : LAST RANK --------------------
    with tabs[9]:
        st.subheader("Last Rank")

        st.markdown("""
- Provisional list title verified  
- Category codes strictly as per prospectus  
- Excluded categories not listed  
- Last rank aligned with allotment  
- Final list published after issue resolution  
""")

    # -------------------- TAB 11 : ALLOTMENT MEMO --------------------
    with tabs[10]:
        st.subheader("Allotment Memo")

        st.markdown("""
- Academic year verified  
- Tuition fees verified (Govt / Self / Mgmt / NRI / Minority)  
- Fee exemptions applied  
- Date of joining correctly shown  
- No joining date for internal change cases  
- Documents listed as per prospectus  
- Font usage verified  
- KIRTADS candidates indicated  
- Footnotes & remarks added  
""")

    # -------------------- TAB 12 : VACANT SEATS --------------------
    with tabs[11]:
        st.subheader("Vacant Seats")

        st.markdown("""
- Unallotted seats verified  
- Non-joining seats verified  
- Transfer Certificate (TC) seats verified  
- Newly added seats included in vacancy calculation  
""")
