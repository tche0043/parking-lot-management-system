-- ================================================
-- Parking Lot Management System Database Schema
-- Microsoft SQL Server
-- ================================================

-- Drop existing objects in correct order
-- Drop stored procedures
IF OBJECT_ID('sp_cleanup_expired_coupons', 'P') IS NOT NULL DROP PROCEDURE sp_cleanup_expired_coupons;

-- Drop triggers
IF OBJECT_ID('tr_parking_record_update', 'TR') IS NOT NULL DROP TRIGGER tr_parking_record_update;
IF OBJECT_ID('tr_parking_lot_update', 'TR') IS NOT NULL DROP TRIGGER tr_parking_lot_update;

-- Drop views
IF OBJECT_ID('vw_current_parking', 'V') IS NOT NULL DROP VIEW vw_current_parking;
IF OBJECT_ID('vw_daily_revenue', 'V') IS NOT NULL DROP VIEW vw_daily_revenue;

-- Drop tables in correct order (foreign key dependencies)
IF OBJECT_ID('PAYMENT_RECORD', 'U') IS NOT NULL DROP TABLE PAYMENT_RECORD;
IF OBJECT_ID('DISCOUNT', 'U') IS NOT NULL DROP TABLE DISCOUNT;
IF OBJECT_ID('PARKING_RECORD', 'U') IS NOT NULL DROP TABLE PARKING_RECORD;
IF OBJECT_ID('ADMIN_LOT_ASSIGNMENTS', 'U') IS NOT NULL DROP TABLE ADMIN_LOT_ASSIGNMENTS;
IF OBJECT_ID('ADMINS', 'U') IS NOT NULL DROP TABLE ADMINS;
IF OBJECT_ID('PARKING_LOT', 'U') IS NOT NULL DROP TABLE PARKING_LOT;

-- 1. Parking Lot Table
CREATE TABLE PARKING_LOT (
    ParkingLotID INT IDENTITY(1,1) PRIMARY KEY,
    Name NVARCHAR(100) NOT NULL,
    Address NVARCHAR(255),
    TotalSpaces INT NOT NULL CHECK (TotalSpaces > 0),
    HourlyRate INT NOT NULL CHECK (HourlyRate > 0),
    DailyMaxRate INT,
    CreatedAt DATETIME2 NOT NULL DEFAULT GETDATE(),
    UpdatedAt DATETIME2 NOT NULL DEFAULT GETDATE()
);

-- Add constraint after table creation
ALTER TABLE PARKING_LOT ADD CONSTRAINT CHK_DailyMaxRate 
CHECK (DailyMaxRate IS NULL OR DailyMaxRate >= HourlyRate);

-- 2. Admins Table
CREATE TABLE ADMINS (
    AdminID INT IDENTITY(1,1) PRIMARY KEY,
    Username NVARCHAR(100) NOT NULL UNIQUE,
    PasswordHash NVARCHAR(255) NOT NULL,
    RoleLevel INT NOT NULL DEFAULT 1 CHECK (RoleLevel IN (1, 99)), -- 1: LotManager, 99: SuperAdmin
    CreatedAt DATETIME2 NOT NULL DEFAULT GETDATE(),
    LastLoginAt DATETIME2,
    IsActive BIT NOT NULL DEFAULT 1
);

-- 3. Admin Lot Assignments Table (Many-to-Many relationship)
CREATE TABLE ADMIN_LOT_ASSIGNMENTS (
    AssignmentID INT IDENTITY(1,1) PRIMARY KEY,
    AdminID INT NOT NULL,
    ParkingLotID INT NOT NULL,
    AssignedAt DATETIME2 NOT NULL DEFAULT GETDATE(),
    AssignedBy INT, -- AdminID of the super admin who made the assignment
    FOREIGN KEY (AdminID) REFERENCES ADMINS(AdminID) ON DELETE CASCADE,
    FOREIGN KEY (ParkingLotID) REFERENCES PARKING_LOT(ParkingLotID) ON DELETE CASCADE,
    FOREIGN KEY (AssignedBy) REFERENCES ADMINS(AdminID),
    UNIQUE (AdminID, ParkingLotID) -- Prevent duplicate assignments
);

-- 4. Parking Record Table
CREATE TABLE PARKING_RECORD (
    RecordID INT IDENTITY(1,1) PRIMARY KEY,
    ParkingLotID INT NOT NULL,
    VehicleNumber NVARCHAR(8) NOT NULL,
    EntryTime DATETIME2 NOT NULL DEFAULT GETDATE(),
    ExitTime DATETIME2,
    PaidUntilTime DATETIME2, -- Grace period deadline after payment
    TotalFee INT, -- Final fee paid (NULL if unpaid)
    CreatedAt DATETIME2 NOT NULL DEFAULT GETDATE(),
    UpdatedAt DATETIME2 NOT NULL DEFAULT GETDATE(),
    FOREIGN KEY (ParkingLotID) REFERENCES PARKING_LOT(ParkingLotID),
    CHECK (ExitTime IS NULL OR ExitTime >= EntryTime),
    CHECK (PaidUntilTime IS NULL OR PaidUntilTime >= EntryTime)
);

-- 5. Discount/Coupon Table
CREATE TABLE DISCOUNT (
    DiscountID INT IDENTITY(1,1) PRIMARY KEY,
    Code NVARCHAR(12) NOT NULL UNIQUE,
    ParkingLotID INT NOT NULL, -- Tied to specific parking lot
    GeneratedTime DATETIME2 NOT NULL DEFAULT GETDATE(),
    ExpiryTime DATETIME2 NOT NULL,
    UsedTime DATETIME2, -- NULL if not used
    RecordID INT, -- NULL if not used, references the parking record where used
    PartnerName NVARCHAR(100), -- Optional partner who generated the coupon
    FOREIGN KEY (ParkingLotID) REFERENCES PARKING_LOT(ParkingLotID),
    FOREIGN KEY (RecordID) REFERENCES PARKING_RECORD(RecordID),
    CHECK (ExpiryTime > GeneratedTime),
    CHECK (UsedTime IS NULL OR UsedTime >= GeneratedTime),
    CHECK (UsedTime IS NULL OR UsedTime <= ExpiryTime),
    CHECK ((UsedTime IS NULL AND RecordID IS NULL) OR (UsedTime IS NOT NULL AND RecordID IS NOT NULL))
);

-- 6. Payment Record Table
CREATE TABLE PAYMENT_RECORD (
    PaymentID INT IDENTITY(1,1) PRIMARY KEY,
    RecordID INT NOT NULL,
    PaymentAmount INT NOT NULL CHECK (PaymentAmount >= 0),
    PaymentMethod NVARCHAR(50) NOT NULL CHECK (PaymentMethod IN ('Cash', 'CreditCard', 'Manual')),
    PaymentTime DATETIME2 NOT NULL DEFAULT GETDATE(),
    TransactionID NVARCHAR(100) UNIQUE,
    ProcessedBy NVARCHAR(100), -- 'System', 'Admin', or specific admin username
    FOREIGN KEY (RecordID) REFERENCES PARKING_RECORD(RecordID)
);

-- ================================================
-- Indexes for Performance
-- ================================================

-- Parking Record Indexes
CREATE INDEX idx_vehicle_number ON PARKING_RECORD(VehicleNumber);
CREATE INDEX idx_parking_lot_entry_time ON PARKING_RECORD(ParkingLotID, EntryTime);
CREATE INDEX idx_entry_time ON PARKING_RECORD(EntryTime);
CREATE INDEX idx_exit_time ON PARKING_RECORD(ExitTime);
CREATE INDEX idx_active_records ON PARKING_RECORD(ParkingLotID, ExitTime) WHERE ExitTime IS NULL;

-- Discount Indexes
CREATE INDEX idx_discount_code ON DISCOUNT(Code);
CREATE INDEX idx_discount_parking_lot ON DISCOUNT(ParkingLotID);
CREATE INDEX idx_discount_expiry ON DISCOUNT(ExpiryTime);
CREATE INDEX idx_active_discounts ON DISCOUNT(ParkingLotID, ExpiryTime, UsedTime) WHERE UsedTime IS NULL;

-- Payment Record Indexes
CREATE INDEX idx_payment_record ON PAYMENT_RECORD(RecordID);
CREATE INDEX idx_payment_time ON PAYMENT_RECORD(PaymentTime);
CREATE INDEX idx_transaction_id ON PAYMENT_RECORD(TransactionID);

-- Admin Indexes
CREATE INDEX idx_admin_username ON ADMINS(Username);
CREATE INDEX idx_admin_role ON ADMINS(RoleLevel, IsActive);

-- ================================================
-- Sample Data for Testing
-- ================================================

-- Insert sample parking lots
INSERT INTO PARKING_LOT (Name, Address, TotalSpaces, HourlyRate, DailyMaxRate) VALUES
('台中市政府停車場', '台中市西屯區台灣大道三段99號', 200, 30, 200),
('逢甲夜市停車場', '台中市西屯區文華路100號', 150, 40, 300),
('一中街停車場', '台中市北區一中街10號', 100, 35, 250),
('台中火車站停車場', '台中市中區建國路1號', 300, 25, 180);

-- Insert sample admins (password is 'admin123' hashed with SHA256)
-- Note: In production, use proper password hashing like bcrypt
INSERT INTO ADMINS (Username, PasswordHash, RoleLevel) VALUES
('superadmin', '240BE518FABD2724DDB6F04EEB1DA5967448D7E831C08C8FA822809F74C720A9', 99),
('manager1', '240BE518FABD2724DDB6F04EEB1DA5967448D7E831C08C8FA822809F74C720A9', 1),
('manager2', '240BE518FABD2724DDB6F04EEB1DA5967448D7E831C08C8FA822809F74C720A9', 1);

-- Assign lot managers to specific parking lots
INSERT INTO ADMIN_LOT_ASSIGNMENTS (AdminID, ParkingLotID, AssignedBy) VALUES
(2, 1, 1), -- manager1 assigned to 台中市政府停車場
(2, 2, 1), -- manager1 assigned to 逢甲夜市停車場  
(3, 3, 1), -- manager2 assigned to 一中街停車場
(3, 4, 1); -- manager2 assigned to 台中火車站停車場

-- Insert sample parking records for testing
INSERT INTO PARKING_RECORD (ParkingLotID, VehicleNumber, EntryTime) VALUES
(1, 'ABC-1234', DATEADD(hour, -2, GETDATE())),
(1, 'XYZ-5678', DATEADD(hour, -1, GETDATE())),
(2, 'DEF-9876', DATEADD(minute, -30, GETDATE())),
(3, 'GHI-5432', DATEADD(hour, -3, GETDATE()));

-- Insert sample discount coupons
INSERT INTO DISCOUNT (Code, ParkingLotID, GeneratedTime, ExpiryTime, PartnerName) VALUES
('COFFEE123456', 1, GETDATE(), DATEADD(hour, 2, GETDATE()), 'Starbucks Coffee'),
('SHOP789012', 2, GETDATE(), DATEADD(hour, 2, GETDATE()), 'Family Mart'),
('MEAL345678', 3, GETDATE(), DATEADD(hour, 2, GETDATE()), 'McDonalds'),
('EXPIRED12', 1, DATEADD(hour, -3, GETDATE()), DATEADD(hour, -1, GETDATE()), 'Test Expired');

-- ================================================
-- Views for Common Queries
-- ================================================
GO

-- View for current parking status
CREATE VIEW vw_current_parking AS
SELECT 
    pr.RecordID,
    pr.VehicleNumber,
    pr.EntryTime,
    pr.PaidUntilTime,
    pr.TotalFee,
    pl.ParkingLotID,
    pl.Name as LotName,
    pl.HourlyRate,
    DATEDIFF(minute, pr.EntryTime, GETDATE()) as ParkingDurationMinutes,
    CASE 
        WHEN pr.PaidUntilTime IS NULL THEN 'Unpaid'
        WHEN pr.PaidUntilTime > GETDATE() THEN 'Paid'
        ELSE 'Payment Expired'
    END as PaymentStatus
FROM PARKING_RECORD pr
JOIN PARKING_LOT pl ON pr.ParkingLotID = pl.ParkingLotID
WHERE pr.ExitTime IS NULL;
GO

-- View for daily revenue summary
CREATE VIEW vw_daily_revenue AS
SELECT 
    pl.ParkingLotID,
    pl.Name as LotName,
    CAST(pr.EntryTime AS DATE) as Date,
    COUNT(pr.RecordID) as TotalEntries,
    COUNT(CASE WHEN pr.ExitTime IS NOT NULL THEN 1 END) as TotalExits,
    COUNT(CASE WHEN pr.TotalFee IS NOT NULL THEN 1 END) as PaidTransactions,
    ISNULL(SUM(pr.TotalFee), 0) as TotalRevenue,
    AVG(CAST(pr.TotalFee as FLOAT)) as AverageRevenue
FROM PARKING_LOT pl
LEFT JOIN PARKING_RECORD pr ON pl.ParkingLotID = pr.ParkingLotID
GROUP BY pl.ParkingLotID, pl.Name, CAST(pr.EntryTime AS DATE);
GO

-- ================================================
-- Triggers for Audit Trail
-- ================================================

-- Trigger to update UpdatedAt timestamp on PARKING_RECORD
CREATE TRIGGER tr_parking_record_update
ON PARKING_RECORD
AFTER UPDATE
AS
BEGIN
    UPDATE PARKING_RECORD 
    SET UpdatedAt = GETDATE()
    WHERE RecordID IN (SELECT RecordID FROM inserted);
END;
GO

-- Trigger to update UpdatedAt timestamp on PARKING_LOT
CREATE TRIGGER tr_parking_lot_update
ON PARKING_LOT
AFTER UPDATE
AS
BEGIN
    UPDATE PARKING_LOT 
    SET UpdatedAt = GETDATE()
    WHERE ParkingLotID IN (SELECT ParkingLotID FROM inserted);
END;
GO

-- ================================================
-- Stored Procedures for Common Operations
-- ================================================

-- Procedure to clean up expired coupons (for scheduled tasks)
CREATE PROCEDURE sp_cleanup_expired_coupons
AS
BEGIN
    DECLARE @expired_count INT, @old_used_count INT;
    
    -- Delete expired unused coupons
    DELETE FROM DISCOUNT 
    WHERE UsedTime IS NULL AND ExpiryTime < GETDATE();
    SET @expired_count = @@ROWCOUNT;
    
    -- Delete old used coupons (older than 24 hours)
    DELETE FROM DISCOUNT 
    WHERE UsedTime IS NOT NULL AND UsedTime < DATEADD(hour, -24, GETDATE());
    SET @old_used_count = @@ROWCOUNT;
    
    SELECT @expired_count as ExpiredCouponsDeleted, @old_used_count as OldUsedCouponsDeleted;
END;

-- ================================================
-- Database Schema Creation Complete
-- ================================================

PRINT 'Database schema created successfully!';
PRINT 'Sample data inserted for testing.';
PRINT 'Default admin credentials:';
PRINT '  Super Admin - Username: superadmin, Password: admin123';
PRINT '  Manager 1 - Username: manager1, Password: admin123';
PRINT '  Manager 2 - Username: manager2, Password: admin123';