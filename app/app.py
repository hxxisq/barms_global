"""
app.py — Barms Global (Streamlit Frontend)

Database operations are strictly decoupled and handled in `data_access.py`.
"""

import io
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit_authenticator as stauth
from data_access import (
    delete_transaction,
    fetch_projects,
    fetch_transactions,
    get_engine,
    insert_transaction,
)

# --- App config ---

st.set_page_config(
    page_title="Barms Global Construction Financials",
    # page_icon="🏗️",
    layout="wide",
)

# --- 1. User Configuration ---

credentials = {
    "usernames": {
        "admin": {
            "name": "Barms Global",
            "password": "$2b$12$xm5pZbFF5q2ETUvIH0i4XugBiWFG6F7LdVSudGhdk4lv7UdmyavT6",
        }
    }
}

# --- 2. Create the Authenticator ---
# Pass the values directly without the named labels (credentials=, etc.)
authenticator = stauth.Authenticate(
    credentials, "construction_financials_auth", "some_random_secret_string", 30
)

# --- 3. Render the Login UI ---
authenticator.login()

# --- 4. Handle the Logic via Session State ---
if st.session_state["authentication_status"] is False:
    st.error("Username/password is incorrect")
    st.stop()  # Halts the app
elif st.session_state["authentication_status"] is None:
    st.warning("Please enter your username and password to access the dashboard")
    st.stop()  # Halts the app

# --- 5. Success! Welcome the User ---
# If the code reaches this line, the user logged in successfully.
st.sidebar.write(f"Welcome back, **{st.session_state['name']}**!")
authenticator.logout(location="sidebar")
st.sidebar.markdown("---")


CATEGORIES = [
    "Labour",
    "Transport & Fuel",
    "Professional Fees",
    "Miscellaneous",
    "Funding",
    "Accommodation",
    "Public Relation",
    "Plumbing",
    "Electrical",
]

BUILD_STAGES = [
    "Foundation",
    "Substructure",
    "Superstructure",
    "Roofing",
    "Finishing",
    "External Works",
    "N/A (Not Applicable)",
]

UNITS = [
    "cbq1",
    "cbq2",
    "cbq19",
    "cbq20",
    "cbq21",
    "shared",
]

# --- Shared: project selector (sidebar) ---

engine = get_engine()


# def sidebar_project_selector() -> tuple[int | None, str | None]:
#     """
#     Renders a project dropdown in the sidebar.
#     Returns (project_id, project_name).
#     If the database fails or is empty, gracefully alerts the user
#     and returns (None, None)
#     """
#     try:
#         projects_df = fetch_projects(engine)
#         if projects_df.empty:
#             raise ValueError("No projects found in the database.")

#         # Build the dictionary mapping: {"Project Name": ID}
#         options = dict(zip(projects_df["project_name"], projects_df["project_id"]))

#     except Exception as e:
#         # Log the error to your terminal so you can debug it behind the scenes
#         print(f"Error fetching projects: {e}")
#         options = {}  # Set to an empty dictionary on failure

#     # --- UI & Safety Check ---
#     # If the dictionary is empty (database failed or is empty), stop here.
#     if not options:
#         st.sidebar.warning("No projects available.")
#         return None, None

#     project_name = st.sidebar.selectbox("Select Project", list(options.keys()))
#     return options[project_name], project_name

def sidebar_project_selector() -> tuple[int | None, str | None]:
    try:
        projects_df = fetch_projects(engine)
        if projects_df.empty:
            raise ValueError("No projects found in the database.")
        options = dict(zip(projects_df["project_name"], projects_df["project_id"]))
    except Exception as e:
        st.sidebar.error(f"DEBUG: {e}")
        return None, None

    if not options:
        st.sidebar.warning("No projects available.")
        return None, None

    project_name = st.sidebar.selectbox("Select Project", list(options.keys()))
    return options[project_name], project_name

# --- Page 1: QS Data Entry ---


def render_qs_form(project_id: int, project_name: str) -> None:
    st.title("Log New Expense")
    st.caption(f"Project: **{project_name}**")
    st.write(
        "Enter daily site transactions. Data syncs immediately "
        "to the master database after submission."
    )

    with st.form("transaction_form", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            t_date = st.date_input("Transaction Date", datetime.today())
            build_stage = st.selectbox("Build Stage", BUILD_STAGES)
            category = st.selectbox("Category", CATEGORIES)
            amount = st.number_input(
                "Amount (₦)", min_value=0.0, step=1000.0, format="%.2f",
                value=None, placeholder="Enter amount..."
            )

        with col2:
            # Auto-derive transaction type from category — no ambiguity
            if category == "Funding":
                t_type = "Credit (Funding)"
                st.info("Transaction type set to **Credit (Funding)** automatically.")
            else:
                t_type = st.radio(
                    "Transaction Type", ["Debit (Expense)", "Credit (Funding)"]
                )
            unit = st.selectbox("Unit", UNITS)
            description = st.text_area(
                "Description / Notes",
                placeholder="e.g. 100 bags of cement @ ₦8,000 each",
            )
        
        submitted = st.form_submit_button("Submit Transaction")

    if submitted:
        # Validation
        errors = []
        if amount is None or amount <= 0:
            errors.append("Amount must be greater than 0.")
        if not description.strip():
            errors.append("Description is required.")

        if errors:
            for e in errors:
                st.error(e)
            return

        is_funding = t_type == "Credit (Funding)"
        credit = (amount or 0.0) if is_funding else 0.0
        debit = (amount or 0.0) if not is_funding else 0.0

        try:
            ok = insert_transaction(
                engine,
                project_id=project_id,
                unit=unit.strip(),
                transaction_date=t_date,
                build_stage=build_stage,
                category=category.lower(),
                description=description.strip(),
                credit=credit,
                debit=debit,
                is_funding=is_funding,
            )
            if ok:
                st.success("Transaction saved successfully!")
        except Exception as exc:
            st.error(f"Database error while saving transaction: {exc}")


# --- Page 2: Executive Dashboard ---


def render_dashboard(project_id: int, project_name: str) -> None:
    st.title("Executive Dashboard")
    st.caption(f"Project: **{project_name}**")

    # --- Date range filter ---
    with st.expander("Filter by date range", expanded=False):
        col_a, col_b = st.columns(2)
        default_start = datetime(datetime.today().year, 1, 1)
        start_date = col_a.date_input("From", default_start)
        end_date = col_b.date_input("To", datetime.today())

    try:
        df = fetch_transactions(
            engine,
            project_id=project_id,
            start_date=str(start_date),
            end_date=str(end_date),
        )
    except Exception as exc:
        st.error(f"Database error while fetching transactions: {exc}")
        return

    if df.empty:
        st.warning("No transactions found for the selected project and date range.")
        return

    # --- KPIs ---
    total_funding = df["credit"].sum()
    total_spent = df["debit"].sum()
    balance = total_funding - total_spent
    # delta_sign = "-" if balance < 0 else ""

    k1, k2, k3 = st.columns(3)
    k1.metric("Total Funding Received", f"₦ {total_funding:,.2f}")
    k2.metric("Total Expenses to Date", f"₦ {total_spent:,.2f}")
    k3.metric(
        "Current Balance",
        f"₦ {balance:,.2f}",
        # delta=f"{delta_sign}₦ {abs(balance):,.2f}",
        # delta_color="normal",
    )

    st.markdown("---")

    # --- Charts & table ----
    col_chart, col_trend = st.columns(2)

    with col_chart:
        st.subheader("Expense Breakdown by Category")
        expenses_df = df[df["is_funding"] == False]  # noqa: E712

        if not expenses_df.empty:
            cat_summary = expenses_df.groupby("category")["debit"].sum().reset_index()

            # 1. Create a custom string for the legend (Name + Value)
            # This creates labels like "Materials<br>₦50,000,000"
            cat_summary["legend_label"] = cat_summary.apply(
                lambda row: f"{row['category'].title()}<br>₦{row['debit']:,.0f}", axis=1
            )

            # 2. Build the Donut Chart
            fig = px.pie(
                cat_summary,
                values="debit",
                names="legend_label",  # Use our new custom label here!
                hole=0.5,
            )

            # 3. Format what shows up on the chart vs. the legend
            fig.update_traces(
                textposition="inside",
                textinfo="percent",  # Only show the % on the colored slices
                hovertemplate="%{label}<br>Percentage: %{percent}<extra></extra>",
            )

            # 4. Position the Legend on the right
            fig.update_layout(
                margin=dict(l=0, r=0, t=40, b=0),
                showlegend=True,  # Turn the legend back on
                legend=dict(
                    orientation="v",  # Vertical layout
                    yanchor="middle",  # Vertically center it
                    y=0.5,
                    xanchor="left",  # Push it to the right of the chart
                    x=1.05,
                    title="",  # Hide the default 'legend_label' title
                ),
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No expense data to chart yet.")

    with col_trend:
        st.subheader("Daily Spend (Last 7 Days)")

        if not expenses_df.empty:
            expenses_df["transaction_date"] = pd.to_datetime(
                expenses_df["transaction_date"]
            )

            cutoff_date = pd.to_datetime(end_date) - timedelta(days=7)
            recent_expenses = expenses_df[expenses_df["transaction_date"] > cutoff_date]

            if not recent_expenses.empty:
                daily_trend = (
                    recent_expenses.groupby(
                        recent_expenses["transaction_date"].dt.date
                    )["debit"]
                    .sum()
                    .reset_index()
                )
                daily_trend.rename(
                    columns={"transaction_date": "Date", "debit": "Amount Spent"},
                    inplace=True,
                )

                # Format the date nicely for a narrow column (e.g., '05-Jun')
                daily_trend["Date"] = pd.to_datetime(daily_trend["Date"]).dt.strftime(
                    "%d-%b"
                )

                fig_trend = px.bar(
                    daily_trend,
                    x="Date",
                    y="Amount Spent",
                    # text_auto=".2s",
                )

                fig_trend.update_traces(
                    texttemplate="%{y:.2s}",
                    marker_color="#89B3BA",
                    textposition="outside",
                )
                fig_trend.update_layout(
                    margin=dict(
                        l=0, r=0, t=40, b=0
                    ),  # Top margin matches the donut chart
                    xaxis_title="",
                    yaxis_title="Amount (₦)",
                    yaxis_tickformat=",",
                )

                st.plotly_chart(fig_trend, use_container_width=True)

            else:
                st.info("No expenses recorded in the last 7 days.")
        else:
            st.info("No expense data available to trend.")

    # --- Full ledger (collapsible) ---
    with st.expander("View full ledger"):
        full = df.copy()
        full["transaction_date"] = pd.to_datetime(full["transaction_date"]).dt.strftime(
            "%d-%b-%Y"
        )

        display_df = full.drop(columns=["project_id", "is_funding"], errors="ignore")
        st.dataframe(display_df, hide_index=True, use_container_width=True)

        # 1. Create an in-memory buffer to hold the binary Excel data
        buffer = io.BytesIO()

        # 2. Write the dataframe to the buffer
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            display_df.to_excel(writer, index=False, sheet_name="Ledger")

        # 3. Create the download button using the buffer's value
        st.download_button(
            label="Export to Excel",
            data=buffer.getvalue(),
            file_name="transactions.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


# --- Page 3: Manage Records (Error Correction) ---


def render_manage_records(project_id: int, project_name: str) -> None:
    st.title("Manage Records")
    st.caption(f"Project: **{project_name}**")
    st.write(
        "Review recent transactions below. If a mistake was made, delete the record here and re-enter it in the Data Entry tab."
    )

    # # Fetch recent transactions (e.g., last 30 days to keep the list manageable)
    # start_date = datetime.today() - timedelta(days=30)
    # end_date = datetime.today()
    col_a, col_b = st.columns(2)
    default_start = datetime.today() - timedelta(days=30)
    start_date = col_a.date_input("From", default_start, key="manage_start")
    end_date = col_b.date_input("To", datetime.today(), key="manage_end")

    df = fetch_transactions(
        engine,
        project_id=project_id,
        start_date=str(start_date),
        end_date=str(end_date),
    )

    if df.empty:
        st.info("No recent transactions found to manage.")
        return

    # Display the recent transactions so the user can identify the mistake
    st.subheader("Recent Transactions (Last 30 Days)")
    display_df = df.drop(columns=["project_id", "is_funding"], errors="ignore")
    st.dataframe(display_df, hide_index=True, use_container_width=True)

    st.markdown("---")

    # Deletion Interface
    st.subheader("Delete an Entry")

    # Create a descriptive label for the dropdown
    # Assuming 'transaction_id' is a column in your dataframe. Adjust if it's named 'id'.
    df["dropdown_label"] = df.apply(
        lambda row: (
            f"ID: {row['transaction_id']} | {row['transaction_date']} | {row['category'].title()} | ₦{row['debit'] if row['debit'] > 0 else row['credit']:,.2f} - {row['description']}"
        ),
        axis=1,
    )

    options = dict(zip(df["dropdown_label"], df["transaction_id"]))

    selected_label = st.selectbox(
        "Select the incorrect transaction to delete:", list(options.keys())
    )

    if st.button("Delete Transaction", type="primary"):
        st.session_state["pending_delete_id"] = options[selected_label]
        st.session_state["pending_delete_label"] = selected_label

    if "pending_delete_id" in st.session_state:
        target_id = st.session_state["pending_delete_id"]
        target_label = st.session_state["pending_delete_label"]

        st.warning(f"Are you sure you want to delete this transaction?")
        st.caption(f"**{target_label}**")

        col_yes, col_no, _ = st.columns([1, 1, 4])

        with col_yes:
            if st.button("Yes, delete", type="primary"):
                success = delete_transaction(engine, target_id)
                del st.session_state["pending_delete_id"]
                del st.session_state["pending_delete_label"]
                if success:
                    st.success(f"Transaction ID {target_id} deleted successfully.")
                    st.rerun()
                else:
                    st.error("Failed to delete the transaction. Check the database connection.")

        with col_no:
            if st.button("Cancel"):
                del st.session_state["pending_delete_id"]
                del st.session_state["pending_delete_label"]
                st.rerun()


# --- Page 4: Data Explorer ---

def render_data_explorer(project_id: int, project_name: str) -> None:
    st.title("Data Explorer")
    st.caption(f"Project: **{project_name}**")
    st.write("Slice and filter all transactions to drill into specific areas of spend.")

    # --- Date range ---
    col_a, col_b = st.columns(2)
    default_start = datetime(datetime.today().year, 1, 1)
    start_date = col_a.date_input("From", default_start, key="explorer_start")
    end_date = col_b.date_input("To", datetime.today(), key="explorer_end")

    df = fetch_transactions(
        engine,
        project_id=project_id,
        start_date=str(start_date),
        end_date=str(end_date),
    )

    if df.empty:
        st.warning("No transactions found for this project and date range.")
        return

    st.markdown("---")

    # --- Filter Panel ---
    st.subheader("Filters")
    f1, f2, f3, f4 = st.columns(4)

    with f1:
        all_categories = sorted(df["category"].dropna().unique().tolist())
        selected_categories = st.multiselect(
            "Category",
            options=all_categories,
            # default=all_categories,
            format_func=lambda x: x.title(),
        )

    with f2:
        all_stages = sorted(df["build_stage"].dropna().unique().tolist())
        selected_stages = st.multiselect(
            "Build Stage",
            options=all_stages,
            # default=all_stages,
        )

    with f3:
        type_options = {"All": None, "Expenses only": False, "Funding only": True}
        selected_type_label = st.selectbox("Transaction Type", list(type_options.keys()))
        selected_type = type_options[selected_type_label]

    with f4:
        all_units = sorted(df["unit"].dropna().unique().tolist())
        selected_units = st.multiselect(
            "Unit",
            options=all_units,
            # default=all_units,
        )

    # --- Apply Filters ---
    filtered = df.copy()

    if selected_categories:
        filtered = filtered[filtered["category"].isin(selected_categories)]
    if selected_stages:
        filtered = filtered[filtered["build_stage"].isin(selected_stages)]
    if selected_type is not None:
        filtered = filtered[filtered["is_funding"] == selected_type]
    if selected_units:
        filtered = filtered[filtered["unit"].isin(selected_units)]

    st.markdown("---")

    if filtered.empty:
        st.info("No transactions match your current filters.")
        return

    # --- KPIs for filtered data ---
    st.subheader(f"Results — {len(filtered):,} transactions")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Funding", f"₦ {filtered['credit'].sum():,.2f}")
    k2.metric("Total Expenses", f"₦ {filtered['debit'].sum():,.2f}")
    k3.metric("Net Balance", f"₦ {(filtered['credit'].sum() - filtered['debit'].sum()):,.2f}")
    k4.metric("Transactions", f"{len(filtered):,}")

    st.markdown("---")

    # --- Chart: group by whichever dimension is most filtered ---
    expenses_only = filtered[filtered["is_funding"] == False]  # noqa: E712
    if not expenses_only.empty:
        # Offer the user a grouping dimension for the chart
        group_by = st.selectbox(
            "Group chart by",
            ["category", "build_stage", "unit"],
            format_func=lambda x: x.replace("_", " ").title(),
        )

        chart_data = (
            expenses_only.groupby(group_by)["debit"]
            .sum()
            .reset_index()
            .sort_values("debit", ascending=False)
        )
        chart_data[group_by] = chart_data[group_by].apply(
            lambda x: x.title() if isinstance(x, str) else x
        )

        fig = px.bar(
            chart_data,
            x=group_by,
            y="debit",
            labels={group_by: group_by.replace("_", " ").title(), "debit": "Amount (₦)"},
        )
        fig.update_traces(marker_color="#89B3BA", texttemplate="₦%{y:,.0f}", textposition="outside")
        fig.update_layout(
            xaxis_title="",
            yaxis_title="Amount (₦)",
            yaxis_tickformat=",",
            margin=dict(l=0, r=0, t=20, b=0),
        )
        st.plotly_chart(fig, use_container_width=True)

    # --- Filtered Ledger ---
    with st.expander("View filtered transactions", expanded=True):
        display_df = filtered.drop(columns=["project_id", "is_funding"], errors="ignore").copy()
        display_df["transaction_date"] = pd.to_datetime(display_df["transaction_date"]).dt.strftime("%d-%b-%Y")
        st.dataframe(display_df, hide_index=True, use_container_width=True)

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            display_df.to_excel(writer, index=False, sheet_name="Filtered Data")

        st.download_button(
            label="Export filtered data to Excel",
            data=buffer.getvalue(),
            file_name="filtered_transactions.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

# --- Navigation ---

st.sidebar.title("Navigation")
app_mode = st.sidebar.radio(
    "Select a View", ["Executive Dashboard", "Data Entry", "Manage Records", "Data Explorer"]
)
st.sidebar.markdown("---")

project_id, project_name = sidebar_project_selector()

st.sidebar.markdown("---")


if project_id is not None and project_name is not None:
    if app_mode == "Data Entry":
        render_qs_form(project_id, project_name)
    elif app_mode == "Executive Dashboard":
        render_dashboard(project_id, project_name)
    elif app_mode == "Manage Records":
        render_manage_records(project_id, project_name)
    elif app_mode == "Data Explorer":
        render_data_explorer(project_id, project_name)
else:
    st.info("Please select or add a project in the sidebar to continue.")