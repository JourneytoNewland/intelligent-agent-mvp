-- 数据库初始化脚本

-- 创建 Langfuse 数据库（如果不存在）
CREATE DATABASE langfuse;

-- 连接到 agent_db
\c agent_db

-- 启用 pgvector 扩展（用于未来可能的向量检索）
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 创建订单事实表
CREATE TABLE IF NOT EXISTS fact_orders (
    id VARCHAR(50) PRIMARY KEY,
    customer_id INTEGER,
    product_id INTEGER,
    region_id INTEGER,
    amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('completed', 'pending', 'cancelled')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 创建客户维度表
CREATE TABLE IF NOT EXISTS dim_customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    region_id INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 创建产品维度表
CREATE TABLE IF NOT EXISTS dim_products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    category VARCHAR(50) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 创建地区维度表
CREATE TABLE IF NOT EXISTS dim_regions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    country VARCHAR(50) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON fact_orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_product_id ON fact_orders(product_id);
CREATE INDEX IF NOT EXISTS idx_orders_region_id ON fact_orders(region_id);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON fact_orders(created_at);
CREATE INDEX IF NOT EXISTS idx_orders_status ON fact_orders(status);

CREATE INDEX IF NOT EXISTS idx_customers_region_id ON dim_customers(region_id);
CREATE INDEX IF NOT EXISTS idx_products_category ON dim_products(category);

-- 创建指标物化视图（定期刷新）
CREATE MATERIALIZED VIEW IF NOT EXISTS metrics AS
SELECT
    date_trunc('day', created_at) as date,
    region_id,
    SUM(amount) as sales_amount,
    COUNT(DISTINCT customer_id) as active_users,
    COUNT(*) as order_count,
    AVG(amount) as avg_order_value
FROM fact_orders
WHERE status = 'completed'
GROUP BY date, region_id
ORDER BY date DESC, region_id;

-- 创建物化视图索引
CREATE UNIQUE INDEX IF NOT EXISTS idx_metrics_date_region ON metrics(date, region_id);
CREATE INDEX IF NOT EXISTS idx_metrics_date ON metrics(date);

-- 创建函数：刷新指标物化视图
CREATE OR REPLACE FUNCTION refresh_metrics()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY metrics;
END;
$$ LANGUAGE plpgsql;

-- 创建 LangGraph checkpoint 表（用于状态持久化）
CREATE TABLE IF NOT EXISTS langgraph_checkpoints (
    thread_id VARCHAR(200) PRIMARY KEY,
    checkpoint_id VARCHAR(200) NOT NULL,
    state JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_checkpoints_thread_id ON langgraph_checkpoints(thread_id);
CREATE INDEX IF NOT EXISTS idx_checkpoints_created_at ON langgraph_checkpoints(created_at);

-- 插入示例地区数据
INSERT INTO dim_regions (name, country) VALUES
    ('华东地区', '中国'),
    ('华南地区', '中国'),
    ('华北地区', '中国'),
    ('西南地区', '中国'),
    ('西北地区', '中国'),
    ('东北地区', '中国'),
    ('华中地区', '中国')
ON CONFLICT DO NOTHING;

-- 插入示例产品类别数据
INSERT INTO dim_products (name, category, price) VALUES
    ('智能手机 Pro', '电子产品', 5999.00),
    ('笔记本电脑 Air', '电子产品', 8999.00),
    ('无线耳机', '配件', 999.00),
    ('智能手表', '可穿戴设备', 2499.00),
    ('平板电脑', '电子产品', 3999.00)
ON CONFLICT DO NOTHING;

-- 创建更新时间戳触发器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_langgraph_checkpoints_updated_at
    BEFORE UPDATE ON langgraph_checkpoints
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 授予必要的权限
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;
