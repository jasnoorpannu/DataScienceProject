"""
Sales Data Analysis Script
Processes online_retail_II.csv and generates JSON for the dashboard UI.
"""
import pandas as pd
import json
import warnings
warnings.filterwarnings('ignore')

print("Loading data...")
df = pd.read_csv('data/online_retail_II.csv', encoding='latin1')

# ── Clean data ──────────────────────────────────────────────────────────────
df = df[~df['Invoice'].astype(str).str.startswith('C')]
df = df[(df['Quantity'] > 0) & (df['Price'] > 0)]
df.dropna(subset=['Description'], inplace=True)

# Parse dates
df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])
df['YearMonth'] = df['InvoiceDate'].dt.to_period('M').astype(str)
df['Year'] = df['InvoiceDate'].dt.year
df['Month'] = df['InvoiceDate'].dt.month
df['MonthName'] = df['InvoiceDate'].dt.strftime('%b')
df['Revenue'] = df['Quantity'] * df['Price']

print(f"Clean records: {len(df):,}")

# ── Descriptive Statistics ──────────────────────────────────────────────────
stats = {
    "total_revenue": round(df['Revenue'].sum(), 2),
    "total_orders": int(df['Invoice'].nunique()),
    "total_customers": int(df['Customer ID'].nunique()),
    "total_products": int(df['Description'].nunique()),
    "avg_order_value": round(df.groupby('Invoice')['Revenue'].sum().mean(), 2),
    "total_units_sold": int(df['Quantity'].sum()),
    "date_range_start": df['InvoiceDate'].min().strftime('%Y-%m-%d'),
    "date_range_end": df['InvoiceDate'].max().strftime('%Y-%m-%d'),
}
print("Stats:", stats)

# ── Monthly Sales Trend ─────────────────────────────────────────────────────
monthly = (
    df.groupby('YearMonth')
    .agg(Revenue=('Revenue', 'sum'), Orders=('Invoice', 'nunique'))
    .reset_index()
    .sort_values('YearMonth')
)
monthly['Revenue'] = monthly['Revenue'].round(2)
monthly_data = monthly.to_dict(orient='records')

# ── Top 10 Products by Revenue ──────────────────────────────────────────────
top_products_rev = (
    df.groupby('Description')['Revenue']
    .sum()
    .nlargest(10)
    .reset_index()
)
top_products_rev.columns = ['product', 'revenue']
top_products_rev['revenue'] = top_products_rev['revenue'].round(2)
top_products_revenue = top_products_rev.to_dict(orient='records')

# ── Top 10 Products by Quantity Sold ───────────────────────────────────────
top_products_qty = (
    df.groupby('Description')['Quantity']
    .sum()
    .nlargest(10)
    .reset_index()
)
top_products_qty.columns = ['product', 'quantity']
top_products_qty['quantity'] = top_products_qty['quantity'].astype(int)
top_products_quantity = top_products_qty.to_dict(orient='records')

# ── Sales by Country (Top 10) ───────────────────────────────────────────────
country_sales = (
    df.groupby('Country')['Revenue']
    .sum()
    .nlargest(10)
    .reset_index()
)
country_sales.columns = ['country', 'revenue']
country_sales['revenue'] = country_sales['revenue'].round(2)
country_data = country_sales.to_dict(orient='records')

# ── Monthly Revenue by Year (for year-over-year comparison) ────────────────
monthly_by_year = (
    df.groupby(['Year', 'Month', 'MonthName'])['Revenue']
    .sum()
    .reset_index()
)
monthly_by_year['Revenue'] = monthly_by_year['Revenue'].round(2)

year_data = {}
for year in sorted(df['Year'].unique()):
    subset = monthly_by_year[monthly_by_year['Year'] == year].sort_values('Month')
    year_data[str(year)] = subset[['Month', 'MonthName', 'Revenue']].to_dict(orient='records')

# ── Category / Product heatmap (top 10 products × top months) ──────────────
top10_products = top_products_rev['product'].tolist()
df_top = df[df['Description'].isin(top10_products)]
heatmap_raw = (
    df_top.groupby(['YearMonth', 'Description'])['Revenue']
    .sum()
    .reset_index()
)
heatmap_raw.columns = ['month', 'product', 'revenue']
heatmap_raw['revenue'] = heatmap_raw['revenue'].round(2)
heatmap_data = heatmap_raw.to_dict(orient='records')

# ── Weekly sales pattern ────────────────────────────────────────────────────
df['DayOfWeek'] = df['InvoiceDate'].dt.day_name()
dow_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
weekly = (
    df.groupby('DayOfWeek')['Revenue']
    .sum()
    .reindex(dow_order)
    .reset_index()
)
weekly.columns = ['day', 'revenue']
weekly['revenue'] = weekly['revenue'].round(2)
weekly_data = weekly.to_dict(orient='records')

# ── Revenue distribution (histogram buckets) ──────────────────────────────
order_revenue = df.groupby('Invoice')['Revenue'].sum()
bins = [0, 50, 100, 200, 500, 1000, 2000, 5000, float('inf')]
labels = ['<£50', '£50-100', '£100-200', '£200-500', '£500-1K', '£1K-2K', '£2K-5K', '>£5K']
hist_counts = pd.cut(order_revenue, bins=bins, labels=labels).value_counts().reindex(labels)
histogram_data = [{'bucket': l, 'count': int(c)} for l, c in zip(labels, hist_counts)]

# ── Assemble final JSON ─────────────────────────────────────────────────────
output = {
    "stats": stats,
    "monthly_trend": monthly_data,
    "top_products_revenue": top_products_revenue,
    "top_products_quantity": top_products_quantity,
    "country_sales": country_data,
    "year_over_year": year_data,
    "weekly_pattern": weekly_data,
    "order_histogram": histogram_data,
    "heatmap": heatmap_data,
}

import os
os.makedirs('dashboard', exist_ok=True)
with open('dashboard/sales_data.json', 'w') as f:
    json.dump(output, f, indent=2)

print("dashboard/sales_data.json written successfully!")
print(f"   Monthly records: {len(monthly_data)}")
print(f"   Top products: {len(top_products_revenue)}")
print(f"   Countries: {len(country_data)}")
