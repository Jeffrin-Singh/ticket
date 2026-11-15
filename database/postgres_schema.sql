-- ==============================================================================
-- Tirupati Automation - PostgreSQL Schema
-- ==============================================================================

-- 1. Logins Table (Replaces user_details.xlsx)
CREATE TABLE logins (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'ACTIVE', -- e.g., 'ACTIVE', 'PASSED', 'BLOCKED'
    last_used_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Family Groups Table (Replaces the unique 'Group' concept in Excel)
CREATE TABLE family_groups (
    id SERIAL PRIMARY KEY,
    group_name VARCHAR(100) UNIQUE NOT NULL,
    target_date DATE, -- The date you want to book for
    status VARCHAR(50) DEFAULT 'PENDING', -- 'PENDING', 'IN_PROGRESS', 'PASSED', 'FAILED'
    payment_method VARCHAR(50) DEFAULT 'UPI', -- 'UPI', 'CARD'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Pilgrims Table (Replaces the individual rows in pilgrims_details.xlsx)
CREATE TABLE pilgrims (
    id SERIAL PRIMARY KEY,
    group_id INTEGER REFERENCES family_groups(id) ON DELETE CASCADE,
    full_name VARCHAR(150) NOT NULL,
    age INTEGER NOT NULL,
    gender VARCHAR(20) NOT NULL,
    aadhar_number VARCHAR(20) UNIQUE NOT NULL,
    -- Add any other specific ID types or fields needed by the form
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Active Sessions Table (Tracks the 10 browsers racing each other)
CREATE TABLE active_sessions (
    id SERIAL PRIMARY KEY,
    group_id INTEGER REFERENCES family_groups(id) ON DELETE CASCADE,
    login_id INTEGER REFERENCES logins(id) ON DELETE SET NULL,
    worker_index INTEGER NOT NULL,
    status VARCHAR(50) DEFAULT 'LAUNCHED', -- 'LAUNCHED', 'CAPTCHA_SOLVED', 'PAYMENT_READY', 'WON', 'LOST'
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ==============================================================================
-- Helpful Indexes for Performance
-- ==============================================================================
CREATE INDEX idx_logins_status ON logins(status);
CREATE INDEX idx_family_groups_status ON family_groups(status);
CREATE INDEX idx_pilgrims_group_id ON pilgrims(group_id);
CREATE INDEX idx_active_sessions_group_id ON active_sessions(group_id);

-- ==============================================================================
-- Optional: Trigger to auto-update the 'updated_at' column on Family Groups
-- ==============================================================================
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_family_groups_modtime
    BEFORE UPDATE ON family_groups
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_column();

-- 5. Payments Table (Stores the payment method details for automation)
CREATE TABLE payments (
    id SERIAL PRIMARY KEY,
    group_id INTEGER REFERENCES family_groups(id) ON DELETE CASCADE UNIQUE,
    payment_type VARCHAR(20) NOT NULL, -- 'UPI', 'CREDIT_CARD', 'DEBIT_CARD'
    
    -- For UPI
    upi_id VARCHAR(100),
    
    -- For Cards (Note: In a real production system, encrypt these!)
    card_number VARCHAR(20),
    card_expiry_month VARCHAR(2),
    card_expiry_year VARCHAR(4),
    card_cvv VARCHAR(4),
    cardholder_name VARCHAR(150),
    
    -- Transaction tracking
    transaction_id VARCHAR(100),
    payment_status VARCHAR(50) DEFAULT 'PENDING', -- 'PENDING', 'INITIATED', 'SUCCESS', 'FAILED'
    amount DECIMAL(10, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Trigger to auto-update 'updated_at' on Payments
CREATE TRIGGER update_payments_modtime
    BEFORE UPDATE ON payments
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_column();
