import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
import seaborn as sns

# Database setup
def init_db():
    conn = sqlite3.connect("inventory.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_name TEXT UNIQUE,
                    quantity INTEGER,
                    cost_price REAL,
                    selling_price REAL,
                    supplier TEXT,
                    expiry_date TEXT
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    expense_name TEXT UNIQUE,
                    amount REAL
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS sales (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_name TEXT,
                    quantity_sold INTEGER,
                    sale_price REAL,
                    date TEXT
                )''')
    conn.commit()
    conn.close()

def add_stock(product_name, quantity, cost_price, selling_price, supplier, expiry_date):
    if not expiry_date:  
        expiry_date = "N/A"
    
    conn = sqlite3.connect("inventory.db")
    c = conn.cursor()
    c.execute('''INSERT INTO inventory (product_name, quantity, cost_price, selling_price, supplier, expiry_date)
                 VALUES (?, ?, ?, ?, ?, ?) 
                 ON CONFLICT(product_name) 
                 DO UPDATE SET quantity = quantity + excluded.quantity''',  # ✅ Use "excluded.quantity" instead
              (product_name, quantity, cost_price, selling_price, supplier, expiry_date))  
    conn.commit()
    conn.close()



# Reduce stock and log sales with sale date
def sell_product(product_name, quantity_sold, sale_price, sale_date):
    conn = sqlite3.connect("inventory.db")
    c = conn.cursor()
    
    # Check if the product exists and has enough stock
    c.execute("SELECT quantity FROM inventory WHERE product_name = ?", (product_name,))
    result = c.fetchone()
    
    if result and result[0] >= quantity_sold:
        new_quantity = result[0] - quantity_sold
        
        # Update inventory
        c.execute("UPDATE inventory SET quantity = ? WHERE product_name = ?", (new_quantity, product_name))
        
        # Insert sale record
        c.execute("INSERT INTO sales (product_name, quantity_sold, sale_price, date) VALUES (?, ?, ?, ?)", 
                  (product_name, quantity_sold, sale_price, sale_date))
        
        conn.commit()
        conn.close()
        return f"✅ {quantity_sold} units of {product_name} sold successfully!"
    
    conn.close()
    return f"❌ Not enough stock for {product_name}!"


# Fetch stock data
def get_stock():
    conn = sqlite3.connect("inventory.db")
    df = pd.read_sql_query("SELECT * FROM inventory", conn)
    conn.close()
    return df

# Add expenses
def add_expense(expense_name, amount):
    conn = sqlite3.connect("inventory.db")
    c = conn.cursor()
    c.execute("INSERT INTO expenses (expense_name, amount) VALUES (?, ?)", (expense_name, amount))
    conn.commit()
    conn.close()

# Fetch sales data
def get_sales():
    conn = sqlite3.connect("inventory.db")
    df = pd.read_sql_query("SELECT * FROM sales", conn)
    conn.close()
    return df

# Fetch expenses
def get_expenses():
    conn = sqlite3.connect("inventory.db")
    df = pd.read_sql_query("SELECT * FROM expenses", conn)
    conn.close()
    return df

# Calculate optimal restocking level
def calculate_restock(stock_data):
    restock_levels = stock_data.copy()
    restock_levels['Restock Suggestion'] = restock_levels['quantity'].apply(lambda x: 'Low Stock - Restock Needed' if x < 10 else 'Sufficient Stock')
    return restock_levels[['product_name', 'quantity', 'Restock Suggestion']]

# Calculate breakeven price
def calculate_breakeven(stock_data):
    stock_data['Breakeven Price'] = stock_data['cost_price'] * 1.25  # Example: 25% margin
    return stock_data[['product_name', 'cost_price', 'selling_price', 'Breakeven Price']]

def delete_product(product_name):
    conn = sqlite3.connect("inventory.db")
    c = conn.cursor()
    
    # Check if the product exists
    c.execute("SELECT * FROM inventory WHERE product_name = ?", (product_name,))
    result = c.fetchone()
    
    if result:
        # Delete the product from the inventory table
        c.execute("DELETE FROM inventory WHERE product_name = ?", (product_name,))
        conn.commit()
        conn.close()
        return f"✅ {product_name} has been removed from inventory!"
    
    conn.close()
    return f"❌ {product_name} not found in inventory!"

# Generate sales ledger
def generate_ledger(timeframe):
    sales_data = get_sales()
    if sales_data.empty:
        return "No sales data available!"
    
    sales_data['date'] = pd.to_datetime(sales_data['date'])
    
    if timeframe == 'Daily':
        filtered_data = sales_data[sales_data['date'] == pd.Timestamp.today().normalize()]
    elif timeframe == 'Weekly':
        filtered_data = sales_data[sales_data['date'] >= pd.Timestamp.today() - pd.DateOffset(weeks=1)]
    elif timeframe == 'Monthly':
        filtered_data = sales_data[sales_data['date'] >= pd.Timestamp.today() - pd.DateOffset(months=1)]
    else:
        filtered_data = sales_data
    
    if filtered_data.empty:
        return "No sales data for the selected period!"
    
    return filtered_data
def generate_sales_report():
    sales_data = get_sales()
    if sales_data.empty:
        return 0, 0  # Return zero if there's no sales data
    total_revenue = (sales_data['quantity_sold'] * sales_data['sale_price']).sum()
    total_items_sold = sales_data['quantity_sold'].sum()
    return total_revenue, total_items_sold

def generate_expense_report():
    expenses_data = get_expenses()
    if expenses_data.empty:
        return 0  # Return zero if there's no expense data
    total_expenses = expenses_data['amount'].sum()
    return total_expenses
    
def generate_reports():
    st.header("📈 Comprehensive Business & Inventory Reports")
    stock_data = get_stock()
    sales_data = get_sales()
    total_revenue, total_items_sold = generate_sales_report()
    total_expenses = generate_expense_report()
    net_profit = total_revenue - total_expenses
    total_stock_value = (stock_data['quantity'] * stock_data['cost_price']).sum()
    total_potential_revenue = (stock_data['quantity'] * stock_data['selling_price']).sum()
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Revenue", f"${total_revenue:.2f}")
    col2.metric("Total Items Sold", total_items_sold)
    col3.metric("Net Profit", f"${net_profit:.2f}")
    col4.metric("Total Stock Value", f"${total_stock_value:.2f}")
    
    st.subheader("Optimal Restocking Analysis")
    restock_data = calculate_restock(stock_data)
    st.dataframe(restock_data)
    
    st.subheader("Breakeven Price Analysis")
    breakeven_data = calculate_breakeven(stock_data)
    st.dataframe(breakeven_data)
    
    st.subheader("📊 Sales Trends")
    if not sales_data.empty:
        plt.figure(figsize=(10, 5))
        sns.lineplot(x=sales_data['date'], y=sales_data['quantity_sold'], marker='o', color='b')
        plt.xticks(rotation=45)
        plt.title("Sales Trend Over Time")
        plt.xlabel("Date")
        plt.ylabel("Units Sold")
        st.pyplot(plt)
        plt.close()
    
    st.subheader("💹 Revenue Distribution by Product")
    if not sales_data.empty:
        plt.figure(figsize=(10, 5))
        sns.barplot(x=sales_data['product_name'], y=sales_data['sale_price'] * sales_data['quantity_sold'], palette='coolwarm')
        plt.xticks(rotation=45)
        plt.title("Revenue by Product")
        plt.xlabel("Product")
        plt.ylabel("Revenue ($)")
        st.pyplot(plt)
        plt.close()
    
    st.subheader("📊 Expense Distribution")
    expense_data = get_expenses()
    if not expense_data.empty:
        plt.figure(figsize=(10, 5))
        sns.barplot(x=expense_data['expense_name'], y=expense_data['amount'], palette='Set2')
        plt.xticks(rotation=45)
        plt.title("Business Expenses")
        plt.xlabel("Expense Type")
        plt.ylabel("Amount ($)")
        st.pyplot(plt)
        plt.close()


# Streamlit UI
st.title("Retail Inventory Management")

# Sidebar navigation
menu = st.sidebar.radio("Navigation", ["Add Stock", "Sell Item", "View Inventory", "Reports", "Expenses", "Alerts", "Demand Analysis","Delete Product","Sales Ledger"])

if menu == "Add Stock":
    st.header("📦 Add New Stock Item")
    product_name = st.text_input("Product Name")
    quantity = st.number_input("Quantity", min_value=1, step=1)
    cost_price = st.number_input("Cost Price", min_value=0.01, step=0.01)
    selling_price = st.number_input("Selling Price", min_value=0.01, step=0.01)
    supplier = st.text_input("Supplier")
    expiry_date = st.date_input("Expiry Date (Optional)", value=None)
    if st.button("Add to Inventory"):
        add_stock(product_name, quantity, cost_price, selling_price, supplier, expiry_date)
        st.success("✅ Stock added successfully!")

elif menu == "Sell Item":
    st.header("🛒 Sell Item")
    stock_data = get_stock()
    
    if not stock_data.empty:
        product_name = st.selectbox("Select Product", stock_data["product_name"].unique())
        quantity_sold = st.number_input("Quantity to Sell", min_value=1, step=1)
        sale_price = st.number_input("Selling Price", min_value=0.01, step=0.01)
        sale_date = st.date_input("Sale Date", pd.Timestamp.today()).strftime('%Y-%m-%d')  # Convert to string format
        
        if st.button("Sell"):
            message = sell_product(product_name, quantity_sold, sale_price, sale_date)
            st.success(message)
    else:
        st.warning("❌ No stock available!")



elif menu == "View Inventory":
    st.header("📋 Inventory List")
    stock_data = get_stock()
    st.dataframe(stock_data)

elif menu == "Reports":
    st.header("📈 Inventory Reports")
    stock_data = get_stock()
    total_stock_value = (stock_data['quantity'] * stock_data['cost_price']).sum()
    total_potential_revenue = (stock_data['quantity'] * stock_data['selling_price']).sum()
    st.metric("Total Stock Value", f"${total_stock_value:.2f}")
    
    st.subheader("Optimal Restocking Analysis")
    restock_data = calculate_restock(stock_data)
    st.dataframe(restock_data)
    
    st.subheader("Breakeven Price Analysis")
    breakeven_data = calculate_breakeven(stock_data)
    st.dataframe(breakeven_data)
    sales_data = get_sales()
    st.metric("Total Stock Value", f"${(stock_data['quantity'] * stock_data['cost_price']).sum():.2f}")
    st.subheader("Sales Trends")
    if not sales_data.empty:
        sales_chart = sales_data.groupby('product_name')['quantity_sold'].sum().sort_values().plot(kind='barh', color='skyblue')
        st.pyplot(sales_chart.get_figure())

elif menu == "Expenses":
    st.header("💰 Business Expenses")
    expense_name = st.text_input("Expense Name")
    amount = st.number_input("Amount", min_value=0.01, step=0.01)
    if st.button("Add Expense"):
        add_expense(expense_name, amount)
        st.success("✅ Expense added successfully!")
    st.dataframe(get_expenses())

elif menu == "Alerts":
    st.header("🚨 Alerts & Recommendations")
    stock_data = get_stock()
    low_stock_alerts = stock_data[stock_data['quantity'] < 10]
    expiring_stock = stock_data[stock_data['expiry_date'] <= pd.Timestamp.today().strftime('%Y-%m-%d')]
    if not low_stock_alerts.empty:
        st.warning("⚠️ Low Stock Alert!")
        st.dataframe(low_stock_alerts[['product_name', 'quantity']])
    if not expiring_stock.empty:
        st.warning("⚠️ Expiring Soon!")
        st.dataframe(expiring_stock[['product_name', 'expiry_date']])

elif menu == "Demand Analysis":
    st.header("📊 Product Demand Analysis")
    sales_data = get_sales()
    if not sales_data.empty:
        demand_chart = sales_data.groupby(['date', 'product_name'])['quantity_sold'].sum().unstack().plot(kind='line', figsize=(10,5))
        st.pyplot(demand_chart.get_figure())
    else:
        st.warning("No sales data available!")

elif menu == "Delete Product":
    st.header("🗑️ Remove Inventory Item")
    
    stock_data = get_stock()
    
    if not stock_data.empty:
        product_name = st.selectbox("Select Product to Remove", stock_data["product_name"].unique())
        
        if st.button("Delete Product"):
            message = delete_product(product_name)
            st.success(message)
    else:
        st.warning("❌ No products available to delete!")

elif menu == "Sales Ledger":
    st.header("📖 Sales Ledger")
    timeframe = st.selectbox("Select Timeframe", ["Daily", "Weekly", "Monthly"])
    ledger_data = generate_ledger(timeframe)
    
    if isinstance(ledger_data, str):
        st.warning(ledger_data)
    else:
        st.dataframe(ledger_data)
        
        buffer = BytesIO()
        ledger_data.to_csv(buffer, index=False)
        buffer.seek(0)
        st.download_button(label="Download Ledger", data=buffer, file_name=f"sales_ledger_{timeframe}.csv", mime="text/csv")

if menu == "Reports":
    generate_reports()

init_db()
