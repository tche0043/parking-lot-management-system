-- 修復觸發器邏輯 - 第二版
USE ParkingLot;
GO

-- 1. 刪除舊觸發器
IF EXISTS (SELECT * FROM sys.triggers WHERE name = 'tr_prevent_duplicate_entry')
    DROP TRIGGER tr_prevent_duplicate_entry;
GO

-- 2. 建立修正版觸發器
CREATE TRIGGER tr_prevent_duplicate_entry
ON PARKING_RECORD
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @VehicleNumber NVARCHAR(8);
    DECLARE @ParkingLotID INT;
    DECLARE @RecordID INT;
    DECLARE @DuplicateCount INT;
    
    -- 取得插入的記錄資訊
    SELECT @VehicleNumber = VehicleNumber, 
           @ParkingLotID = ParkingLotID, 
           @RecordID = RecordID
    FROM inserted;
    
    -- 檢查是否有其他相同車牌在同一停車場的活躍記錄
    SELECT @DuplicateCount = COUNT(*)
    FROM PARKING_RECORD 
    WHERE VehicleNumber = @VehicleNumber 
      AND ParkingLotID = @ParkingLotID 
      AND ExitTime IS NULL
      AND RecordID != @RecordID; -- 排除當前插入的記錄
    
    -- 如果發現重複，回滾交易並拋出錯誤
    IF @DuplicateCount > 0
    BEGIN
        DECLARE @ErrorMsg NVARCHAR(200) = '車輛 ' + @VehicleNumber + ' 已在停車場內，無法重複進入同一停車場';
        RAISERROR(@ErrorMsg, 16, 1);
        ROLLBACK TRANSACTION;
        RETURN;
    END;
END;
GO

PRINT '✅ 修正版觸發器建立完成';

-- 3. 重新測試觸發器
PRINT '=== 重新測試觸發器功能 ===';

-- 測試 1: 插入第一筆記錄（應該成功）
BEGIN TRY
    INSERT INTO PARKING_RECORD (ParkingLotID, VehicleNumber, EntryTime)
    VALUES (1, 'TEST-888', GETDATE());
    PRINT '✅ 第一次插入成功';
END TRY
BEGIN CATCH
    PRINT '❌ 第一次插入失敗: ' + ERROR_MESSAGE();
END CATCH;

-- 測試 2: 插入重複記錄（應該失敗）
BEGIN TRY
    INSERT INTO PARKING_RECORD (ParkingLotID, VehicleNumber, EntryTime)
    VALUES (1, 'TEST-888', GETDATE());
    PRINT '❌ 重複插入不應該成功！';
END TRY
BEGIN CATCH
    PRINT '✅ 重複插入被正確阻止: ' + ERROR_MESSAGE();
END CATCH;

-- 測試 3: 在不同停車場插入相同車牌（應該成功）
BEGIN TRY
    INSERT INTO PARKING_RECORD (ParkingLotID, VehicleNumber, EntryTime)
    VALUES (2, 'TEST-888', GETDATE());
    PRINT '✅ 不同停車場插入成功';
END TRY
BEGIN CATCH
    PRINT '❌ 不同停車場插入失敗: ' + ERROR_MESSAGE();
END CATCH;

-- 清理測試資料
DELETE FROM PARKING_RECORD WHERE VehicleNumber = 'TEST-888';
PRINT '測試資料已清理';

-- 4. 再建立唯一索引（現在應該可以成功）
PRINT '=== 嘗試建立唯一索引 ===';
BEGIN TRY
    CREATE UNIQUE INDEX idx_unique_active_vehicle 
    ON PARKING_RECORD (VehicleNumber, ParkingLotID)
    WHERE ExitTime IS NULL;
    PRINT '✅ 唯一索引建立成功';
END TRY
BEGIN CATCH
    PRINT '❌ 唯一索引建立失敗: ' + ERROR_MESSAGE();
    
    -- 顯示現有重複記錄
    PRINT '=== 現有重複記錄 ===';
    SELECT 
        VehicleNumber, 
        ParkingLotID, 
        COUNT(*) as 重複數量,
        STRING_AGG(CAST(RecordID as NVARCHAR), ', ') as 記錄ID們
    FROM PARKING_RECORD 
    WHERE ExitTime IS NULL
    GROUP BY VehicleNumber, ParkingLotID
    HAVING COUNT(*) > 1;
END CATCH;