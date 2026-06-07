import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
from PIL import Image
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import db

# ─── PAGE CONFIG ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="LHC — Legendary House Café",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── INIT DB ─────────────────────────────────────────────────────────────────
@st.cache_resource
def init():
    db.init_db()
    return True

init()

# ─── CURRENCY HELPER ─────────────────────────────────────────────────────────
def rs(amount):
    """Format a number as Nepali Rupees."""
    try:
        return f"Rs {float(amount):,.2f}"
    except Exception:
        return f"Rs {amount}"

# ─── FLASH MESSAGE HELPERS ────────────────────────────────────────────────────
def flash(msg, level="success"):
    """Queue a message to display after st.rerun()."""
    st.session_state["_flash_msg"] = msg
    st.session_state["_flash_level"] = level

def show_flash():
    """Render and clear any queued flash message."""
    if "_flash_msg" in st.session_state:
        msg = st.session_state.pop("_flash_msg")
        level = st.session_state.pop("_flash_level", "success")
        if level == "success":
            st.success(msg)
        elif level == "error":
            st.error(msg)
        elif level == "warning":
            st.warning(msg)
        else:
            st.info(msg)

# ─── SESSION HELPERS ─────────────────────────────────────────────────────────
SESSION_TIMEOUT_HOURS = 24

def is_logged_in():
    if "user" not in st.session_state or not st.session_state.user:
        return False
    login_time = st.session_state.get("login_time")
    if not login_time:
        return False
    if (datetime.now() - login_time).total_seconds() > SESSION_TIMEOUT_HOURS * 3600:
        st.session_state.user = None
        return False
    return True

def is_admin():
    return is_logged_in() and st.session_state.user.get("role") == "admin"

def require_login():
    if not is_logged_in():
        st.warning("Please log in to continue.")
        st.stop()

def require_admin():
    require_login()
    if not is_admin():
        st.error("🔒 Admin access required.")
        st.stop()

# ─── TODAY SESSION ───────────────────────────────────────────────────────────
def get_today():
    return date.today()

def ensure_day_session():
    today = get_today()
    if is_logged_in():
        sess = db.get_or_create_session(today, st.session_state.user["id"])
        st.session_state.day_session = sess

# ─── LOGO + HEADER ───────────────────────────────────────────────────────────
def show_header():
    logo_path = os.path.join(os.path.dirname(__file__), "static", "logo.jpg")
    col1, col2 = st.columns([1, 7])
    with col1:
        if os.path.exists(logo_path):
            st.image(logo_path, use_container_width=True)
    with col2:
        st.markdown("### ☕ Legendary House Café")
        st.caption(f"Today: {get_today().strftime('%A, %B %d, %Y')}")

# ─── CSS TWEAKS ───────────────────────────────────────────────────────────────
def inject_css():
    st.markdown("""
    <style>
    section[data-testid="stSidebar"] button { border-radius: 8px !important; margin-bottom: 2px !important; }
    [data-testid="metric-container"] { background: #fff8f0; border-radius: 10px; padding: 12px; border: 1px solid #e8d5b7; }
    .block-container { padding-top: 1.2rem !important; }
    @media (max-width: 768px) { .block-container { padding-left: 0.5rem !important; padding-right: 0.5rem !important; } }
    </style>
    """, unsafe_allow_html=True)

# ─── LOGIN PAGE ──────────────────────────────────────────────────────────────
def login_page():
    inject_css()
    logo_path = os.path.join(os.path.dirname(__file__), "static", "logo.jpg")
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if os.path.exists(logo_path):
            st.image(logo_path, use_container_width=True)
        st.markdown("## Legendary House Café")
        st.markdown("#### Operations Management System")
        st.divider()
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter username")
            password = st.text_input("Password", type="password", placeholder="Enter password")
            submitted = st.form_submit_button("Sign In", use_container_width=True, type="primary")
            if submitted:
                if not username or not password:
                    st.error("Please enter username and password.")
                else:
                    user = db.verify_user(username, password)
                    if user:
                        st.session_state.user = user
                        st.session_state.login_time = datetime.now()
                        st.session_state.page = "Dashboard"
                        st.rerun()
                    else:
                        st.error("❌ Invalid username or password.")

# ─── SIDEBAR NAV ─────────────────────────────────────────────────────────────
def sidebar_nav():
    ensure_day_session()
    with st.sidebar:
        logo_path = os.path.join(os.path.dirname(__file__), "static", "logo.jpg")
        if os.path.exists(logo_path):
            st.image(logo_path, width=120)
        st.markdown(f"**{st.session_state.user['full_name']}**")
        st.caption(f"Role: {st.session_state.user['role'].title()}")
        st.divider()

        pages = [
            ("📊", "Dashboard"),
            ("📦", "Inventory"),
            ("🔧", "Equipment"),
            ("📋", "Recipes"),
            ("🛒", "Sales"),
            ("🗑️", "Waste Log"),
            ("💸", "Expenses"),
        ]
        if is_admin():
            pages.append(("🔐", "Admin Panel"))

        if "page" not in st.session_state:
            st.session_state.page = "Dashboard"

        for icon, name in pages:
            active = st.session_state.page == name
            if st.button(
                f"{icon} {name}",
                key=f"nav_{name}",
                use_container_width=True,
                type="primary" if active else "secondary",
            ):
                st.session_state.page = name
                st.rerun()

        st.divider()
        day = st.session_state.get("day_session", {})
        status = day.get("status", "open")
        st.caption(f"📅 Session: **{status.upper()}**")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.user = None
            st.session_state.login_time = None
            st.session_state.page = "Dashboard"
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGES
# ══════════════════════════════════════════════════════════════════════════════

# ─── DASHBOARD ───────────────────────────────────────────────────────────────
def page_dashboard():
    inject_css()
    show_header()
    show_flash()
    st.title("📊 Dashboard")
    today = get_today()

    try:
        summary = db.get_daily_summary(today)
        _, top_items = db.get_daily_sales_summary(today)
        alerts = db.get_restock_alerts()
        low_stock = db.get_low_stock_goods()
    except Exception as e:
        st.error(f"Database error loading dashboard: {e}")
        return

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("💰 Revenue Today", rs(summary['revenue']))
    col2.metric("💸 Expenses Today", rs(summary['expenses']))
    profit = summary['profit']
    col3.metric("📈 Net Profit", rs(profit), delta=rs(profit))
    col4.metric("🧾 Transactions", summary["sales_count"])

    st.divider()

    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("🏆 Top Selling Items Today")
        if top_items:
            df_top = pd.DataFrame(top_items)
            fig = px.bar(df_top, x="recipe_name", y="revenue",
                         color="qty", color_continuous_scale="Oranges",
                         labels={"recipe_name": "Item", "revenue": "Revenue (Rs)", "qty": "Qty"},
                         height=300)
            fig.update_layout(showlegend=False, margin=dict(l=0, r=0, t=20, b=0))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No sales recorded today yet.")

        st.subheader("📈 7-Day Revenue Trend")
        try:
            trend = db.get_revenue_trend(7)
            if trend:
                df_trend = pd.DataFrame(trend)
                fig2 = px.line(df_trend, x="session_date", y="revenue",
                               markers=True, height=250,
                               labels={"session_date": "Date", "revenue": "Revenue (Rs)"})
                fig2.update_traces(line_color="#8B4513", marker_color="#D2691E")
                fig2.update_layout(margin=dict(l=0, r=0, t=20, b=0))
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("No historical data yet.")
        except Exception as e:
            st.warning(f"Could not load trend: {e}")

    with col_right:
        st.subheader("⚠️ Restock Alerts")
        if alerts:
            for a in alerts[:10]:
                poss = int(a["possible_drinks"]) if a["possible_drinks"] is not None else 0
                color = "🔴" if poss < 5 else "🟡"
                st.markdown(f"{color} **{a['name']}** — {poss} × {a['recipe_name']}")
        else:
            st.success("✅ All stocks sufficient (≥10 drinks)")

        if low_stock:
            st.subheader("📉 Low Stock")
            for item in low_stock[:6]:
                st.warning(f"**{item['name']}**: {float(item['quantity']):.1f} {item['unit']}")

        st.subheader("📋 Quick Stats")
        day = st.session_state.get("day_session", {})
        st.info(f"Session: **{day.get('status','open').upper()}**")
        st.info(f"Waste entries today: **{summary['waste_count']}**")
        if summary["revenue"] > 0:
            margin = (float(profit) / float(summary["revenue"])) * 100
            st.info(f"Profit margin: **{margin:.1f}%**")


# ─── INVENTORY ───────────────────────────────────────────────────────────────
def page_inventory():
    require_login()
    inject_css()
    show_header()
    show_flash()
    st.title("📦 Inventory — Goods")

    tab1, tab2, tab3 = st.tabs(["📋 View Stock", "➕ Add Good", "🔄 Restock"])

    with tab1:
        goods = db.get_goods()
        if goods:
            df = pd.DataFrame(goods)
            df = df[["name", "category", "unit", "unit_price", "quantity", "reorder_point", "description"]].copy()
            df.columns = ["Name", "Category", "Unit", "Unit Price (Rs)", "Qty", "Reorder Point", "Notes"]
            df["Unit Price (Rs)"] = df["Unit Price (Rs)"].apply(lambda x: float(x))
            df["Qty"] = df["Qty"].apply(lambda x: float(x))

            def highlight_low(row):
                rp = row["Reorder Point"]
                if rp and float(rp) > 0 and float(row["Qty"]) <= float(rp):
                    return ["background-color: #ffe0e0"] * len(row)
                return [""] * len(row)

            col_s, col_c = st.columns([3, 2])
            search = col_s.text_input("🔍 Search goods", placeholder="Type to filter...")
            cats = sorted(set(g["category"] for g in goods if g["category"]))
            cat_filter = col_c.selectbox("Category", ["All"] + cats)

            if search:
                df = df[df["Name"].str.contains(search, case=False, na=False)]
            if cat_filter != "All":
                df = df[df["Category"] == cat_filter]
            st.dataframe(df.style.apply(highlight_low, axis=1), use_container_width=True, height=450)
        else:
            st.info("No goods in inventory yet.")

        if is_admin():
            st.divider()
            st.subheader("✏️ Edit a Good")
            goods_list = db.get_goods()
            if goods_list:
                options = {f"{g['name']} ({g['category']})": g for g in goods_list}
                sel = st.selectbox("Select item to edit", list(options.keys()), key="edit_good_sel")
                g = options[sel]
                with st.form("edit_good_form"):
                    c1, c2 = st.columns(2)
                    name = c1.text_input("Name", g["name"])
                    category = c2.text_input("Category", g["category"])
                    c3, c4 = st.columns(2)
                    unit = c3.text_input("Unit", g["unit"])
                    unit_price = c4.number_input("Unit Price (Rs)", value=float(g["unit_price"]), min_value=0.0, step=0.0001, format="%.4f")
                    c5, c6 = st.columns(2)
                    quantity = c5.number_input("Current Qty", value=float(g["quantity"]), min_value=0.0, step=0.1)
                    reorder = c6.number_input("Reorder Point", value=float(g["reorder_point"]), min_value=0.0, step=0.1)
                    desc = st.text_area("Notes", g.get("description", "") or "")
                    if st.form_submit_button("💾 Save Changes", type="primary"):
                        db.update_good(g["id"], name, category, unit, unit_price, quantity, reorder, desc)
                        flash("✅ Good updated!")
                        st.rerun()
                if st.button("🗑️ Deactivate This Item", key="deact_good"):
                    db.deactivate_good(g["id"])
                    flash("Item deactivated.")
                    st.rerun()

    with tab2:
        st.subheader("Add New Good")
        with st.form("add_good_form"):
            c1, c2 = st.columns(2)
            name = c1.text_input("Item Name *")
            category = c2.text_input("Category *", placeholder="Coffee, Dairy, Syrup, etc.")
            c3, c4 = st.columns(2)
            unit = c3.text_input("Unit *", placeholder="g, ml, pcs, kg, L")
            unit_price = c4.number_input("Unit Price (Rs)", min_value=0.0, step=0.0001, format="%.4f",
                                          help="Cost per unit e.g. 0.003 per ml of milk")
            c5, c6 = st.columns(2)
            quantity = c5.number_input("Opening Quantity", min_value=0.0, step=0.1)
            reorder = c6.number_input("Reorder Point", min_value=0.0, step=0.1,
                                       help="Alert when stock falls below this")
            desc = st.text_area("Notes / Description")
            if st.form_submit_button("✅ Add Item", type="primary"):
                if not name or not category or not unit:
                    st.error("Name, Category and Unit are required.")
                else:
                    db.add_good(name, category, unit, unit_price, quantity, reorder, desc)
                    flash(f"✅ '{name}' added to inventory!")
                    st.rerun()

    with tab3:
        st.subheader("🔄 Restock Items")
        goods_list = db.get_goods()
        if goods_list:
            options = {f"{g['name']} ({g['unit']}) — Current: {float(g['quantity']):.1f}": g for g in goods_list}
            with st.form("restock_form"):
                sel = st.selectbox("Select Item to Restock", list(options.keys()))
                g = options[sel]
                added_qty = st.number_input("Quantity to Add", min_value=0.1, step=0.1)
                reason = st.text_input("Reason / Note", "Restock delivery")
                if st.form_submit_button("📦 Restock", type="primary"):
                    db.restock_good(g["id"], added_qty, st.session_state.user["id"], reason)
                    flash(f"✅ Restocked {added_qty} {g['unit']} of {g['name']}")
                    st.rerun()
        else:
            st.info("No goods to restock.")


# ─── EQUIPMENT ───────────────────────────────────────────────────────────────
def page_equipment():
    require_login()
    inject_css()
    show_header()
    show_flash()
    st.title("🔧 Equipment")

    tab1, tab2 = st.tabs(["📋 View Equipment", "➕ Add Equipment"])

    with tab1:
        equip = db.get_equipment()
        if equip:
            df = pd.DataFrame(equip)
            df["total_value"] = df["unit_price"].astype(float) * df["quantity"].astype(float)
            total_value = df["total_value"].sum()
            display = df[["name", "category", "quantity", "unit_price", "total_value", "condition", "notes"]].copy()
            display.columns = ["Name", "Category", "Qty", "Unit Price (Rs)", "Total Value (Rs)", "Condition", "Notes"]
            search = st.text_input("🔍 Search equipment")
            if search:
                display = display[display["Name"].str.contains(search, case=False, na=False)]
            st.dataframe(display, use_container_width=True, height=400)
            st.info(f"**Total Equipment Value: {rs(total_value)}**")
        else:
            st.info("No equipment recorded.")

        if is_admin():
            st.divider()
            st.subheader("✏️ Edit Equipment")
            equip = db.get_equipment()
            if equip:
                opts = {f"{e['name']} ({e['category']})": e for e in equip}
                sel = st.selectbox("Select equipment to edit", list(opts.keys()), key="edit_eq")
                e = opts[sel]
                condition_opts = ["Good", "Fair", "Needs Repair", "Out of Service"]
                cond_idx = condition_opts.index(e["condition"]) if e["condition"] in condition_opts else 0
                with st.form("edit_eq_form"):
                    c1, c2 = st.columns(2)
                    name = c1.text_input("Name", e["name"])
                    category = c2.text_input("Category", e["category"])
                    c3, c4 = st.columns(2)
                    qty = c3.number_input("Quantity", value=int(e["quantity"]), min_value=0)
                    price = c4.number_input("Unit Price (Rs)", value=float(e["unit_price"]), min_value=0.0, step=0.01)
                    cond = st.selectbox("Condition", condition_opts, index=cond_idx)
                    notes = st.text_area("Notes", e.get("notes", "") or "")
                    if st.form_submit_button("💾 Save", type="primary"):
                        db.update_equipment(e["id"], name, category, qty, price, cond, notes)
                        flash("✅ Equipment updated!")
                        st.rerun()
                if st.button("🗑️ Deactivate", key="deact_eq"):
                    db.deactivate_equipment(e["id"])
                    flash("Equipment deactivated.")
                    st.rerun()

    with tab2:
        with st.form("add_eq_form"):
            c1, c2 = st.columns(2)
            name = c1.text_input("Equipment Name *")
            category = c2.text_input("Category *", placeholder="Coffee Equipment, Kitchen, etc.")
            c3, c4 = st.columns(2)
            qty = c3.number_input("Quantity", min_value=1, value=1)
            price = c4.number_input("Unit Price (Rs)", min_value=0.0, step=0.01)
            c5, c6 = st.columns(2)
            cond = c5.selectbox("Condition", ["Good", "Fair", "Needs Repair"])
            purchase_date = c6.date_input("Purchase Date (optional)", value=None)
            notes = st.text_area("Notes")
            if st.form_submit_button("✅ Add Equipment", type="primary"):
                if not name or not category:
                    st.error("Name and Category are required.")
                else:
                    db.add_equipment(name, category, qty, price, cond, purchase_date, notes)
                    flash(f"✅ '{name}' added!")
                    st.rerun()


# ─── RECIPES ─────────────────────────────────────────────────────────────────
def page_recipes():
    require_login()
    inject_css()
    show_header()
    show_flash()
    st.title("📋 Recipes")

    tab1, tab2, tab3 = st.tabs(["📖 View Recipes", "➕ Add Recipe", "✏️ Edit Recipe"])

    with tab1:
        recipes = db.get_recipes()
        if recipes:
            search = st.text_input("🔍 Search recipes")
            cat_opts = ["All"] + sorted(set(r["category"] for r in recipes if r["category"]))
            cat_f = st.selectbox("Category", cat_opts)

            filtered = recipes
            if search:
                filtered = [r for r in filtered if search.lower() in r["name"].lower()]
            if cat_f != "All":
                filtered = [r for r in filtered if r["category"] == cat_f]

            for r in filtered:
                cost = db.get_recipe_cost(r["id"])
                margin_str = ""
                if float(r['selling_price']) > 0:
                    margin = ((float(r['selling_price']) - cost) / float(r['selling_price'])) * 100
                    margin_str = f"  |  Margin: {margin:.1f}%"
                with st.expander(f"☕ **{r['name']}** — {rs(r['selling_price'])}  |  {r['category']}{margin_str}"):
                    ings = db.get_recipe_ingredients(r["id"])
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        if ings:
                            st.markdown("**Ingredients:**")
                            for i in ings:
                                ing_cost = float(i['quantity_used']) * float(i['unit_price'])
                                st.markdown(f"- {i['good_name']}: **{float(i['quantity_used']):.3g} {i['unit']}**  *(Rs {ing_cost:.4f})*")
                        if r.get("description"):
                            st.caption(r["description"])
                    with col2:
                        st.metric("Selling Price", rs(r['selling_price']))
                        st.metric("Ingredient Cost", f"Rs {cost:.4f}")
                        if float(r['selling_price']) > 0:
                            margin = ((float(r['selling_price']) - cost) / float(r['selling_price'])) * 100
                            st.metric("Gross Margin", f"{margin:.1f}%")
        else:
            st.info("No recipes yet.")

    with tab2:
        goods_list = db.get_goods()
        if not goods_list:
            st.warning("No goods in inventory. Add goods first.")
        else:
            good_opts = {f"{g['name']} ({g['unit']})": g for g in goods_list}

            # ── Number of ingredients OUTSIDE the form so it triggers rerun ──
            if "add_recipe_num_ing" not in st.session_state:
                st.session_state.add_recipe_num_ing = 1

            num_ing = st.number_input(
                "Number of ingredients",
                min_value=1, max_value=10,
                value=st.session_state.add_recipe_num_ing,
                key="add_recipe_num_ing",
                help="Change this to add or remove ingredient rows"
            )

            with st.form("add_recipe_form"):
                c1, c2 = st.columns(2)
                rname = c1.text_input("Recipe Name *")
                rcat = c2.text_input("Category *", placeholder="Coffee, Tea, Food, etc.")
                c3, c4 = st.columns(2)
                rprice = c3.number_input("Selling Price (Rs) *", min_value=0.0, step=0.50)
                rdesc = c4.text_input("Description (optional)")

                st.markdown("**Ingredients**")
                ingredients = []
                for i in range(int(st.session_state.add_recipe_num_ing)):
                    ca, cb, cc = st.columns([3, 2, 2])
                    ing_sel = ca.selectbox(f"Ingredient {i+1}", ["— select —"] + list(good_opts.keys()), key=f"ing_{i}")
                    ing_qty = cb.number_input(f"Quantity", min_value=0.001, value=1.0, step=0.1, key=f"qty_{i}", format="%.3f")
                    ing_unit = cc.text_input(f"Unit", key=f"unit_{i}", placeholder="g/ml/pcs")
                    if ing_sel != "— select —":
                        g = good_opts[ing_sel]
                        ingredients.append({"good_id": g["id"], "quantity": ing_qty, "unit": ing_unit or g["unit"]})

                submitted = st.form_submit_button("✅ Create Recipe", type="primary")
                if submitted:
                    if not rname or not rcat or rprice <= 0:
                        st.error("Name, Category, and Selling Price (>0) are required.")
                    elif not ingredients:
                        st.error("Select at least one ingredient.")
                    else:
                        db.add_recipe(rname, rcat, rprice, rdesc, ingredients)
                        flash(f"✅ Recipe '{rname}' created!")
                        st.rerun()

    with tab3:
        recipes = db.get_recipes()
        if not recipes:
            st.info("No recipes yet.")
        else:
            goods_list = db.get_goods()
            good_opts = {f"{g['name']} ({g['unit']})": g for g in goods_list}
            recipe_opts = {r["name"]: r for r in recipes}
            sel = st.selectbox("Select Recipe to Edit", list(recipe_opts.keys()), key="edit_recipe_sel")
            r = recipe_opts[sel]
            ings = db.get_recipe_ingredients(r["id"])

            # ── Number of ingredients OUTSIDE the form ──
            edit_key = f"edit_recipe_num_ing_{r['id']}"
            if edit_key not in st.session_state:
                st.session_state[edit_key] = max(1, len(ings))

            edit_num_ing = st.number_input(
                "Number of ingredients",
                min_value=1, max_value=10,
                value=st.session_state[edit_key],
                key=edit_key,
                help="Change this to add or remove ingredient rows"
            )

            with st.form("edit_recipe_form"):
                c1, c2 = st.columns(2)
                rname = c1.text_input("Recipe Name", r["name"])
                rcat = c2.text_input("Category", r["category"])
                c3, c4 = st.columns(2)
                rprice = c3.number_input("Selling Price (Rs)", value=float(r["selling_price"]), min_value=0.0, step=0.50)
                rdesc = c4.text_input("Description", r.get("description", "") or "")

                st.markdown("**Ingredients** (replaces existing list)")
                new_ings = []
                ing_opts_list = ["— select —"] + list(good_opts.keys())

                for i in range(int(st.session_state[edit_key])):
                    ca, cb, cc = st.columns([3, 2, 2])
                    default_ing = "— select —"
                    default_qty = 1.0
                    default_unit = ""
                    if i < len(ings):
                        existing = ings[i]
                        default_key = f"{existing['good_name']} ({existing['good_unit']})"
                        if default_key in good_opts:
                            default_ing = default_key
                        default_qty = float(existing["quantity_used"])
                        default_unit = existing["unit"] or existing["good_unit"]
                    def_idx = ing_opts_list.index(default_ing) if default_ing in ing_opts_list else 0
                    ing_sel = ca.selectbox(f"Ingredient {i+1}", ing_opts_list, index=def_idx, key=f"edit_ing_{i}")
                    ing_qty = cb.number_input(f"Qty", min_value=0.001, value=default_qty, step=0.1, key=f"edit_qty_{i}", format="%.3f")
                    ing_unit = cc.text_input(f"Unit", key=f"edit_unit_{i}", value=default_unit)
                    if ing_sel != "— select —":
                        g = good_opts[ing_sel]
                        new_ings.append({"good_id": g["id"], "quantity": ing_qty, "unit": ing_unit or g["unit"]})

                if st.form_submit_button("💾 Update Recipe", type="primary"):
                    if not new_ings:
                        st.error("Add at least one ingredient.")
                    else:
                        db.update_recipe(r["id"], rname, rcat, rprice, rdesc, new_ings)
                        flash("✅ Recipe updated!")
                        st.rerun()

            if is_admin():
                if st.button("🗑️ Deactivate Recipe", key="deact_recipe"):
                    db.deactivate_recipe(r["id"])
                    flash("Recipe deactivated.")
                    st.rerun()


# ─── SALES ───────────────────────────────────────────────────────────────────
def page_sales():
    require_login()
    inject_css()
    show_header()
    show_flash()
    st.title("🛒 Sales")
    today = get_today()

    tab1, tab2 = st.tabs(["➕ Record Sale", "📋 Today's Sales"])

    with tab1:
        recipes = db.get_recipes()
        if not recipes:
            st.warning("No recipes defined. Add recipes first.")
            return

        by_cat = {}
        for r in recipes:
            by_cat.setdefault(r["category"], []).append(r)

        # ── All controls outside any form so total updates live on every change ──
        st.subheader("New Sale Entry")
        cat_list = sorted(by_cat.keys()) + ["Other"]

        chosen_cat = st.selectbox("Category", cat_list, key="sale_cat_select")

        is_other = chosen_cat == "Other"
        recipe = None
        chosen_item = None
        custom_item_name = ""

        if is_other:
            custom_item_name = st.text_input(
                "Item Name *",
                placeholder="Enter item name for custom/unlisted sale...",
                key="sale_custom_name"
            )
        else:
            items_in_cat = by_cat.get(chosen_cat, [])
            item_opts = {r["name"]: r for r in items_in_cat}
            chosen_item = st.selectbox(
                "Menu Item",
                list(item_opts.keys()) if item_opts else ["—"],
                key="sale_item_select"
            )
            recipe = item_opts.get(chosen_item)

        # Auto-fill price when recipe/category changes
        current_recipe_id = recipe["id"] if recipe else None
        if st.session_state.get("_sale_last_recipe_id") != current_recipe_id:
            st.session_state["sale_unit_price"] = float(recipe["selling_price"]) if recipe else 0.0
            st.session_state["_sale_last_recipe_id"] = current_recipe_id
        if "sale_unit_price" not in st.session_state:
            st.session_state["sale_unit_price"] = 0.0

        c3, c4 = st.columns(2)
        unit_price = c3.number_input("Unit Price (Rs)", min_value=0.0, step=0.50, key="sale_unit_price")
        quantity = c4.number_input("Quantity", min_value=1, value=1, step=1, key="sale_quantity")
        discount = st.number_input("Discount (Rs)", min_value=0.0, value=0.0, step=0.50, key="sale_discount")
        comment = st.text_area("Comment / Notes (optional)",
                               placeholder="e.g. no sugar, extra shot, customer name...",
                               key="sale_comment")

        total = unit_price * quantity
        final_total = max(0.0, total - discount)
        ct1, ct2 = st.columns(2)
        ct1.metric("💰 Subtotal", rs(total))
        ct2.metric("✅ After Discount", rs(final_total))

        if st.button("✅ Record Sale", type="primary", use_container_width=True):
            if is_other:
                if not custom_item_name:
                    st.error("Please enter an item name for the 'Other' sale.")
                else:
                    db.add_sale(today, None, custom_item_name, quantity, unit_price, comment,
                                st.session_state.user["id"], discount)
                    flash(f"✅ Sale recorded: {quantity}× {custom_item_name} = {rs(final_total)}")
                    st.rerun()
            elif recipe and chosen_item != "—":
                db.add_sale(today, recipe["id"], recipe["name"], quantity, unit_price, comment,
                            st.session_state.user["id"], discount)
                flash(f"✅ Sale recorded: {quantity}× {recipe['name']} = {rs(final_total)}")
                st.rerun()
            else:
                st.error("Please select a valid category and item.")

    with tab2:
        sales = db.get_sales(today)
        if sales:
            df = pd.DataFrame(sales)
            total_rev = float(df["total_price"].sum())
            total_disc = float(df["discount"].sum()) if "discount" in df.columns else 0.0
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Revenue Today", rs(total_rev))
            c2.metric("Transactions", len(df))
            c3.metric("Total Discounts", rs(total_disc))
            display_cols = ["created_at", "recipe_name", "quantity", "unit_price", "discount", "total_price", "staff_name", "comment"]
            available = [c for c in display_cols if c in df.columns]
            display = df[available].copy()
            display["created_at"] = pd.to_datetime(display["created_at"]).dt.strftime("%H:%M")
            col_names = {"created_at": "Time", "recipe_name": "Item", "quantity": "Qty",
                         "unit_price": "Unit Price (Rs)", "discount": "Discount (Rs)", "total_price": "Total (Rs)",
                         "staff_name": "Staff", "comment": "Comment"}
            display.rename(columns=col_names, inplace=True)
            st.dataframe(display, use_container_width=True, height=350)

            if is_admin():
                st.divider()
                st.subheader("✏️ Edit / Delete Sale Entry")
                sale_opts = {f"#{s['id']} {s['recipe_name']} x{s['quantity']} ({rs(s['total_price'])})": s for s in sales}
                sel_sale = st.selectbox("Select sale entry", list(sale_opts.keys()), key="edit_sale_sel")
                s = sale_opts[sel_sale]
                with st.form("edit_sale_form"):
                    c1, c2, c3 = st.columns(3)
                    sq = c1.number_input("Quantity", value=int(s["quantity"]), min_value=1)
                    sp = c2.number_input("Unit Price (Rs)", value=float(s["unit_price"]), min_value=0.0, step=0.50)
                    sd = c3.number_input("Discount (Rs)", value=float(s.get("discount", 0) or 0), min_value=0.0, step=0.50)
                    sc = st.text_area("Comment", s.get("comment", "") or "")
                    if st.form_submit_button("💾 Update Sale", type="primary"):
                        db.update_sale(s["id"], sq, sp, sc, sd)
                        flash("✅ Sale updated!")
                        st.rerun()
                if st.button("🗑️ Delete This Sale", key="del_sale"):
                    db.delete_sale(s["id"])
                    flash("Sale deleted.")
                    st.rerun()
        else:
            st.info("No sales recorded today.")


# ─── WASTE LOG ───────────────────────────────────────────────────────────────
def page_waste():
    require_login()
    inject_css()
    show_header()
    show_flash()
    st.title("🗑️ Waste Log")
    today = get_today()

    tab1, tab2 = st.tabs(["➕ Log Waste", "📋 Today's Waste"])

    with tab1:
        goods = db.get_goods()
        recipes = db.get_recipes()

        with st.form("waste_form"):
            item_type = st.radio("Type", ["Ingredient (Good)", "Recipe Item"], horizontal=True)
            if item_type == "Ingredient (Good)":
                if not goods:
                    st.warning("No goods available.")
                    st.stop()
                opts = {f"{g['name']} ({g['unit']})": g for g in goods}
                sel = st.selectbox("Select Ingredient", list(opts.keys()))
                g = opts[sel]
                item_id = g["id"]
                item_name = g["name"]
                default_unit = g["unit"]
                db_type = "good"
            else:
                if not recipes:
                    st.warning("No recipes available.")
                    st.stop()
                opts = {r["name"]: r for r in recipes}
                sel = st.selectbox("Select Recipe Item", list(opts.keys()))
                r = opts[sel]
                item_id = r["id"]
                item_name = r["name"]
                default_unit = "pcs"
                db_type = "recipe"

            c1, c2 = st.columns(2)
            qty = c1.number_input("Quantity Wasted", min_value=0.001, step=0.1, format="%.3f")
            unit = c2.text_input("Unit", value=default_unit)
            reason = st.selectbox("Reason", [
                "Spoiled", "Expired", "Dropped/Spilled", "Over-prepared",
                "Quality issue", "Equipment failure", "Other"
            ])
            comment = st.text_area("Additional Comment")
            if st.form_submit_button("📝 Log Waste", type="primary"):
                db.add_waste(today, db_type, item_id, item_name, qty, unit, reason, comment,
                             st.session_state.user["id"])
                flash(f"✅ Waste logged: {qty} {unit} of {item_name}")
                st.rerun()

    with tab2:
        waste = db.get_waste_log(today)
        if waste:
            df = pd.DataFrame(waste)
            display = df[["created_at", "item_name", "quantity", "unit", "reason", "staff_name", "comment"]].copy()
            display["created_at"] = pd.to_datetime(display["created_at"]).dt.strftime("%H:%M")
            display.columns = ["Time", "Item", "Qty", "Unit", "Reason", "Staff", "Comment"]
            st.dataframe(display, use_container_width=True, height=350)

            if is_admin():
                st.divider()
                st.subheader("✏️ Edit / Delete Waste Entry")
                opts = {f"#{w['id']} {w['item_name']} ({float(w['quantity']):.3g} {w['unit']})": w for w in waste}
                sel = st.selectbox("Select entry", list(opts.keys()), key="edit_waste_sel")
                w = opts[sel]
                with st.form("edit_waste_form"):
                    c1, c2 = st.columns(2)
                    wq = c1.number_input("Quantity", value=float(w["quantity"]), min_value=0.001, step=0.1)
                    wu = c2.text_input("Unit", w.get("unit", ""))
                    wr = st.text_input("Reason", w.get("reason", ""))
                    wc = st.text_area("Comment", w.get("comment", "") or "")
                    if st.form_submit_button("💾 Update", type="primary"):
                        db.update_waste(w["id"], wq, wu, wr, wc)
                        flash("✅ Waste log updated!")
                        st.rerun()
                if st.button("🗑️ Delete Entry", key="del_waste"):
                    db.delete_waste(w["id"])
                    flash("Waste entry deleted.")
                    st.rerun()
        else:
            st.info("No waste logged today.")


# ─── EXPENSES ────────────────────────────────────────────────────────────────
def page_expenses():
    require_login()
    inject_css()
    show_header()
    show_flash()
    st.title("💸 Ad-hoc Expenses")
    today = get_today()

    tab1, tab2 = st.tabs(["➕ Add Expense", "📋 Today's Expenses"])

    EXPENSE_CATS = ["Supplies", "Utilities", "Maintenance", "Salary/Wages",
                    "Marketing", "Rent", "Transport", "Food/Ingredients",
                    "Equipment", "Other"]
    PAYMENT_METHODS = ["Cash", "Card", "Transfer", "Other"]

    with tab1:
        with st.form("expense_form"):
            st.subheader("New Expense Entry")
            desc = st.text_input("Description *", placeholder="e.g. Cups delivery, cleaning supplies...")
            c1, c2 = st.columns(2)
            category = c1.selectbox("Category", EXPENSE_CATS)
            amount = c2.number_input("Amount (Rs) *", min_value=0.01, step=0.50)
            c3, c4 = st.columns(2)
            payment = c3.selectbox("Payment Method", PAYMENT_METHODS)
            comment = c4.text_input("Reference / Comment")
            if st.form_submit_button("✅ Add Expense", type="primary"):
                if not desc:
                    st.error("Description is required.")
                else:
                    db.add_expense(today, desc, category, amount, payment, comment,
                                   st.session_state.user["id"])
                    flash(f"✅ Expense recorded: {desc} — {rs(amount)}")
                    st.rerun()

    with tab2:
        expenses = db.get_expenses(today)
        if expenses:
            df = pd.DataFrame(expenses)
            total_exp = float(df["amount"].sum())
            c1, c2 = st.columns(2)
            c1.metric("Total Expenses Today", rs(total_exp))
            c2.metric("Expense Entries", len(df))
            display_cols = ["created_at", "description", "category", "amount", "payment_method", "staff_name", "comment"]
            available = [c for c in display_cols if c in df.columns]
            display = df[available].copy()
            display["created_at"] = pd.to_datetime(display["created_at"]).dt.strftime("%H:%M")
            display.columns = ["Time", "Description", "Category", "Amount (Rs)", "Payment", "Staff", "Comment"][:len(available)]
            st.dataframe(display, use_container_width=True, height=350)

            if len(df) > 1:
                fig = px.pie(df, values="amount", names="category", title="Expenses by Category",
                             color_discrete_sequence=px.colors.sequential.Oranges_r)
                fig.update_layout(margin=dict(l=0, r=0, t=40, b=0))
                st.plotly_chart(fig, use_container_width=True)

            if is_admin():
                st.divider()
                st.subheader("✏️ Edit / Delete Expense")
                opts = {f"#{e['id']} {e['description']} ({rs(e['amount'])})": e for e in expenses}
                sel = st.selectbox("Select entry", list(opts.keys()), key="edit_exp_sel")
                e = opts[sel]
                cur_cat_idx = EXPENSE_CATS.index(e["category"]) if e["category"] in EXPENSE_CATS else 0
                cur_pay_idx = PAYMENT_METHODS.index(e["payment_method"]) if e.get("payment_method") in PAYMENT_METHODS else 0
                with st.form("edit_exp_form"):
                    c1, c2 = st.columns(2)
                    edesc = c1.text_input("Description", e["description"])
                    ecat = c2.selectbox("Category", EXPENSE_CATS, index=cur_cat_idx)
                    c3, c4 = st.columns(2)
                    eamt = c3.number_input("Amount (Rs)", value=float(e["amount"]), min_value=0.01, step=0.50)
                    epay = c4.selectbox("Payment", PAYMENT_METHODS, index=cur_pay_idx)
                    ecom = st.text_input("Comment", e.get("comment", "") or "")
                    if st.form_submit_button("💾 Update", type="primary"):
                        db.update_expense(e["id"], edesc, ecat, eamt, epay, ecom)
                        flash("✅ Expense updated!")
                        st.rerun()
                if st.button("🗑️ Delete Entry", key="del_exp"):
                    db.delete_expense(e["id"])
                    flash("Expense entry deleted.")
                    st.rerun()
        else:
            st.info("No expenses recorded today.")


# ─── ADMIN PANEL ─────────────────────────────────────────────────────────────
def page_admin():
    require_admin()
    inject_css()
    show_header()
    show_flash()
    st.title("🔐 Admin Panel")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "👥 Users", "📊 Full Logs", "📦 Stock History",
        "📅 Sessions", "📈 Reports"
    ])

    with tab1:
        st.subheader("User Management")
        users = db.get_all_users()
        df = pd.DataFrame(users)
        if not df.empty:
            st.dataframe(df[["username", "full_name", "role", "created_at"]], use_container_width=True)

        st.subheader("➕ Create User")
        with st.form("create_user"):
            c1, c2 = st.columns(2)
            uname = c1.text_input("Username *")
            fname = c2.text_input("Full Name *")
            c3, c4 = st.columns(2)
            pwd = c3.text_input("Password *", type="password")
            role = c4.selectbox("Role", ["staff", "admin"])
            if st.form_submit_button("✅ Create User", type="primary"):
                if not uname or not pwd or not fname:
                    st.error("All fields required.")
                else:
                    try:
                        db.create_user(uname, pwd, role, fname)
                        flash(f"✅ User '{uname}' created!")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Error creating user: {ex}")

        st.subheader("🔑 Reset Password")
        if users:
            user_opts = {f"{u['username']} ({u['full_name']})": u for u in users}
            with st.form("reset_pw"):
                sel_u = st.selectbox("Select User", list(user_opts.keys()))
                new_pw = st.text_input("New Password *", type="password")
                conf_pw = st.text_input("Confirm Password *", type="password")
                if st.form_submit_button("🔑 Reset Password", type="primary"):
                    if not new_pw:
                        st.error("Password cannot be empty.")
                    elif new_pw != conf_pw:
                        st.error("Passwords do not match.")
                    else:
                        u = user_opts[sel_u]
                        db.update_user_password(u["id"], new_pw)
                        flash("✅ Password reset successfully!")

        st.subheader("🗑️ Delete User")
        del_opts = {f"{u['username']} ({u['full_name']})": u for u in users if u["username"] != "admin"}
        if del_opts:
            with st.form("del_user"):
                sel_del = st.selectbox("Select User to Delete", list(del_opts.keys()))
                confirm = st.checkbox("I confirm I want to delete this user")
                if st.form_submit_button("Delete User", type="secondary"):
                    if confirm:
                        u = del_opts[sel_del]
                        db.delete_user(u["id"])
                        flash("✅ User deleted.")
                        st.rerun()
                    else:
                        st.warning("Check the confirmation box first.")
        else:
            st.info("No deletable users (admin cannot be deleted).")

    with tab2:
        st.subheader("All Logs")
        log_type = st.selectbox("Log Type", ["Sales", "Waste", "Expenses"])
        col1, col2 = st.columns(2)
        from_date = col1.date_input("From", value=date.today() - timedelta(days=7))
        to_date = col2.date_input("To", value=date.today())

        try:
            if log_type == "Sales":
                rows = db.get_sales(limit=1000)
            elif log_type == "Waste":
                rows = db.get_waste_log(limit=1000)
            else:
                rows = db.get_expenses(limit=1000)
        except Exception as e:
            st.error(f"Error loading logs: {e}")
            rows = []

        if rows:
            df = pd.DataFrame(rows)
            df["session_date"] = pd.to_datetime(df["session_date"]).dt.date
            df = df[(df["session_date"] >= from_date) & (df["session_date"] <= to_date)]
            st.dataframe(df, use_container_width=True, height=450)
            if not df.empty:
                if log_type == "Sales":
                    st.metric("Total Revenue", rs(float(df['total_price'].sum())))
                elif log_type == "Expenses":
                    st.metric("Total Expenses", rs(float(df['amount'].sum())))
        else:
            st.info("No records found.")

    with tab3:
        st.subheader("Stock Adjustment History")
        try:
            adjustments = db.get_stock_adjustments(500)
        except Exception as e:
            st.error(f"Error: {e}")
            adjustments = []
        if adjustments:
            df = pd.DataFrame(adjustments)
            available = [c for c in ["created_at", "good_name", "adjustment_type", "quantity", "previous_qty", "new_qty", "reason", "staff_name"] if c in df.columns]
            display = df[available].copy()
            if "created_at" in display.columns:
                display["created_at"] = pd.to_datetime(display["created_at"]).dt.strftime("%Y-%m-%d %H:%M")
            st.dataframe(display, use_container_width=True, height=400)
        else:
            st.info("No stock adjustments recorded.")

    with tab4:
        st.subheader("Daily Sessions")
        try:
            sessions = db.get_sessions(30)
        except Exception as e:
            st.error(f"Error: {e}")
            sessions = []
        if sessions:
            df = pd.DataFrame(sessions)
            available = [c for c in ["session_date", "status", "opened_name", "closed_name", "closed_at", "notes"] if c in df.columns]
            st.dataframe(df[available], use_container_width=True)
        day_sess = st.session_state.get("day_session", {})
        if day_sess and day_sess.get("status") == "open":
            st.divider()
            st.subheader("Close Today's Session")
            with st.form("close_session"):
                notes = st.text_area("Closing Notes")
                if st.form_submit_button("🔒 Close Session", type="secondary"):
                    db.close_session(day_sess["id"], st.session_state.user["id"], notes)
                    flash("✅ Session closed.")
                    st.rerun()

    with tab5:
        st.subheader("📈 Business Reports")
        col1, col2 = st.columns(2)
        rp_from = col1.date_input("From", value=date.today() - timedelta(days=30), key="rp_from")
        rp_to = col2.date_input("To", value=date.today(), key="rp_to")

        try:
            rev_data, exp_data, top_items = db.get_report_data(rp_from, rp_to)
        except Exception as e:
            st.error(f"Error loading report: {e}")
            rev_data, exp_data, top_items = [], [], []

        if rev_data or exp_data:
            df_rev = pd.DataFrame(rev_data) if rev_data else pd.DataFrame({"session_date": [], "revenue": []})
            df_exp = pd.DataFrame(exp_data) if exp_data else pd.DataFrame({"session_date": [], "expenses": []})
            merged = pd.merge(df_rev, df_exp, on="session_date", how="outer").fillna(0)
            # Cast to float to avoid Decimal vs float arithmetic errors
            merged["revenue"] = merged["revenue"].astype(float)
            merged["expenses"] = merged["expenses"].astype(float)
            merged["profit"] = merged["revenue"] - merged["expenses"]
            fig = px.line(merged, x="session_date", y=["revenue", "expenses", "profit"],
                          title="Revenue vs Expenses vs Profit", markers=True,
                          labels={"session_date": "Date", "value": "Rs"},
                          color_discrete_map={"revenue": "#2ecc71", "expenses": "#e74c3c", "profit": "#8B4513"})
            st.plotly_chart(fig, use_container_width=True)

            c1, c2, c3 = st.columns(3)
            c1.metric("Total Revenue", rs(merged['revenue'].sum()))
            c2.metric("Total Expenses", rs(merged['expenses'].sum()))
            c3.metric("Net Profit", rs(merged['profit'].sum()))
        else:
            st.info("No data in selected date range.")

        if top_items:
            df_top = pd.DataFrame(top_items)
            fig2 = px.bar(df_top, x="recipe_name", y="qty", title="Top Selling Items (by quantity)",
                          color="revenue", color_continuous_scale="Oranges",
                          labels={"recipe_name": "Item", "qty": "Units Sold", "revenue": "Revenue (Rs)"})
            st.plotly_chart(fig2, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN ROUTER
# ══════════════════════════════════════════════════════════════════════════════

def main():
    if not is_logged_in():
        login_page()
        return

    sidebar_nav()
    page = st.session_state.get("page", "Dashboard")

    if page == "Dashboard":
        page_dashboard()
    elif page == "Inventory":
        page_inventory()
    elif page == "Equipment":
        page_equipment()
    elif page == "Recipes":
        page_recipes()
    elif page == "Sales":
        page_sales()
    elif page == "Waste Log":
        page_waste()
    elif page == "Expenses":
        page_expenses()
    elif page == "Admin Panel":
        page_admin()


if __name__ == "__main__":
    main()
