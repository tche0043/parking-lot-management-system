// Parking Lot Management System - Admin Dashboard JavaScript

// API Configuration - Use window global to ensure accessibility in all scopes
window.API_BASE_URL = window.location.origin;
const API_BASE_URL = window.API_BASE_URL;

// Global state
let currentAdmin = null;
let currentLots = [];

// Initialize application
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Check if user is logged in
    checkAuthStatus();
    
    // Bind event listeners
    bindEventListeners();
    
    // Initialize date inputs with current date range
    const today = new Date().toISOString().split('T')[0];
    const lastMonth = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
    
    document.getElementById('report-start-date').value = lastMonth;
    document.getElementById('report-end-date').value = today;
}

function bindEventListeners() {
    // Navigation
    document.querySelectorAll('.nav-link[data-page]').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const page = this.getAttribute('data-page');
            showPage(page);
            
            // Update active nav item
            document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
            this.classList.add('active');
        });
    });
    
    // Login form
    document.getElementById('login-form').addEventListener('submit', handleLogin);
    
    // Logout
    document.getElementById('logout-btn').addEventListener('click', handleLogout);
    
    // Manual action form
    document.getElementById('manual-action').addEventListener('change', function() {
        const amountGroup = document.getElementById('amount-group');
        if (this.value === 'mark_paid') {
            amountGroup.style.display = 'block';
        } else {
            amountGroup.style.display = 'none';
        }
    });
    
    // Lot selector
    document.getElementById('lot-selector').addEventListener('change', loadVehicles);
}

async function checkAuthStatus() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/admin/profile`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const admin = await response.json();
            currentAdmin = admin;
            showDashboard();
            updateUIForRole();
        } else {
            showLoginModal();
        }
    } catch (error) {
        console.error('Auth check failed:', error);
        showLoginModal();
    }
}

function showLoginModal() {
    const modal = new bootstrap.Modal(document.getElementById('loginModal'));
    modal.show();
}

async function handleLogin(e) {
    e.preventDefault();
    
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const errorDiv = document.getElementById('login-error');
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/admin/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            currentAdmin = data.admin;
            bootstrap.Modal.getInstance(document.getElementById('loginModal')).hide();
            showDashboard();
            updateUIForRole();
        } else {
            errorDiv.textContent = data.error || '登入失敗';
            errorDiv.classList.remove('d-none');
        }
    } catch (error) {
        errorDiv.textContent = '連線錯誤，請稍後再試';
        errorDiv.classList.remove('d-none');
    }
}

async function handleLogout() {
    try {
        await fetch(`${API_BASE_URL}/api/v1/admin/logout`, {
            method: 'POST',
            credentials: 'include'
        });
    } catch (error) {
        console.error('Logout error:', error);
    }
    
    currentAdmin = null;
    showLoginModal();
}

function updateUIForRole() {
    if (!currentAdmin) return;
    
    document.getElementById('current-admin-username').textContent = currentAdmin.username;
    
    // Show super admin menu if applicable
    if (currentAdmin.roleLevel === 99) {
        document.getElementById('super-admin-menu').style.display = 'block';
        document.getElementById('add-lot-btn').style.display = 'inline-block';
    }
}

function showPage(pageId) {
    // Hide all pages
    document.querySelectorAll('.page-content').forEach(page => {
        page.style.display = 'none';
    });
    
    // Show target page
    const targetPage = document.getElementById(`${pageId}-page`);
    if (targetPage) {
        targetPage.style.display = 'block';
        
        // Load page-specific data
        switch (pageId) {
            case 'dashboard':
                loadDashboard();
                break;
            case 'lots':
                loadParkingLots();
                break;
            case 'vehicles':
                loadVehiclesPage();
                break;
            case 'reports':
                loadReportsPage();
                break;
            case 'admins':
                loadAdminsPage();
                break;
        }
    }
}

function showDashboard() {
    showPage('dashboard');
    document.querySelector('.nav-link[data-page="dashboard"]').classList.add('active');
}

async function loadDashboard() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/admin/dashboard`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            
            document.getElementById('total-lots').textContent = data.totalLots;
            document.getElementById('today-revenue').textContent = `$${data.todayRevenue.toLocaleString()}`;
            document.getElementById('current-occupancy').textContent = data.currentOccupancy;
            document.getElementById('today-entries').textContent = data.todayEntries;
            
            loadLotsOverview();
        }
    } catch (error) {
        console.error('Dashboard load error:', error);
    }
}

async function loadLotsOverview() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/admin/lots`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            currentLots = data.lots;
            
            const container = document.getElementById('lots-overview');
            container.innerHTML = '';
            
            data.lots.forEach(lot => {
                const occupancyRate = Math.round((lot.currentOccupancy / lot.totalSpaces) * 100);
                const statusClass = occupancyRate > 80 ? 'high' : occupancyRate > 50 ? 'medium' : 'low';
                
                const card = document.createElement('div');
                card.className = 'col-md-6 col-lg-4 mb-3';
                card.innerHTML = `
                    <div class="card">
                        <div class="card-body">
                            <h6 class="card-title">${lot.name}</h6>
                            <p class="card-text text-muted-light">${lot.address}</p>
                            <div class="d-flex justify-content-between mb-2">
                                <span>使用率</span>
                                <span class="fw-bold">${occupancyRate}%</span>
                            </div>
                            <div class="occupancy-bar mb-2">
                                <div class="occupancy-fill ${statusClass}" style="width: ${occupancyRate}%"></div>
                            </div>
                            <div class="d-flex justify-content-between">
                                <small class="text-muted">在場: ${lot.currentOccupancy}</small>
                                <small class="text-muted">總計: ${lot.totalSpaces}</small>
                            </div>
                        </div>
                    </div>
                `;
                container.appendChild(card);
            });
        }
    } catch (error) {
        console.error('Lots overview load error:', error);
    }
}

async function refreshDashboard() {
    const button = event.target;
    const originalText = button.innerHTML;
    button.innerHTML = '<i class="bi bi-arrow-clockwise spinner-border spinner-border-sm me-1"></i>重新整理';
    button.disabled = true;
    
    await loadDashboard();
    
    setTimeout(() => {
        button.innerHTML = originalText;
        button.disabled = false;
    }, 1000);
}

async function loadParkingLots() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/admin/lots`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            const tableBody = document.getElementById('lots-table-body');
            tableBody.innerHTML = '';
            
            data.lots.forEach(lot => {
                const occupancyRate = Math.round((lot.currentOccupancy / lot.totalSpaces) * 100);
                
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td class="fw-semibold">${lot.name}</td>
                    <td class="text-muted-light">${lot.address}</td>
                    <td>${lot.totalSpaces}</td>
                    <td>${lot.currentOccupancy}</td>
                    <td>
                        <span class="badge ${occupancyRate > 80 ? 'badge-danger' : occupancyRate > 50 ? 'badge-warning' : 'badge-success'}">
                            ${occupancyRate}%
                        </span>
                    </td>
                    <td>$${lot.hourlyRate}</td>
                    <td>$${lot.dailyMaxRate || '-'}</td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary" onclick="viewLotDetails(${lot.id})">
                            <i class="bi bi-eye"></i>
                        </button>
                    </td>
                `;
                tableBody.appendChild(row);
            });
        }
    } catch (error) {
        console.error('Parking lots load error:', error);
    }
}

async function loadVehiclesPage() {
    // Load lot selector options
    await loadLotSelector();
    
    // Load vehicles for first available lot
    loadVehicles();
}

async function loadLotSelector() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/admin/lots`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            const selector = document.getElementById('lot-selector');
            const reportSelector = document.getElementById('report-lot');
            
            // Clear existing options (except first)
            selector.innerHTML = '<option value="">選擇停車場</option>';
            reportSelector.innerHTML = '<option value="">所有停車場</option>';
            
            data.lots.forEach(lot => {
                const option = new Option(lot.name, lot.id);
                const reportOption = new Option(lot.name, lot.id);
                selector.appendChild(option);
                reportSelector.appendChild(reportOption);
            });
            
            // Auto-select first lot if available
            if (data.lots.length > 0) {
                selector.value = data.lots[0].id;
            }
        }
    } catch (error) {
        console.error('Lot selector load error:', error);
    }
}

async function loadVehicles() {
    const lotId = document.getElementById('lot-selector').value;
    if (!lotId) return;
    
    try {
        // Load current vehicles
        const currentResponse = await fetch(`${API_BASE_URL}/api/v1/admin/lots/${lotId}/vehicles?status=current`, {
            credentials: 'include'
        });
        
        if (currentResponse.ok) {
            const currentData = await currentResponse.json();
            displayCurrentVehicles(currentData.vehicles);
        }
        
        // Load vehicle history
        const historyResponse = await fetch(`${API_BASE_URL}/api/v1/admin/lots/${lotId}/vehicles?status=history&days=7`, {
            credentials: 'include'
        });
        
        if (historyResponse.ok) {
            const historyData = await historyResponse.json();
            displayVehicleHistory(historyData.vehicles);
        }
    } catch (error) {
        console.error('Vehicles load error:', error);
    }
}

function displayCurrentVehicles(vehicles) {
    const tableBody = document.getElementById('current-vehicles-body');
    tableBody.innerHTML = '';
    
    vehicles.forEach(vehicle => {
        const entryTime = new Date(vehicle.entryTime);
        const paidUntilTime = vehicle.paidUntilTime ? new Date(vehicle.paidUntilTime) : null;
        
        const statusBadge = getPaymentStatusBadge(vehicle.paymentStatus);
        
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="fw-semibold">${vehicle.licensePlate}</td>
            <td>${entryTime.toLocaleString()}</td>
            <td>${statusBadge}</td>
            <td>${paidUntilTime ? paidUntilTime.toLocaleString() : '-'}</td>
            <td>$${vehicle.currentFee !== undefined ? vehicle.currentFee : (vehicle.totalFee || 0)}</td>
            <td>
                <button class="btn btn-sm btn-outline-secondary" onclick="openManualAction(${vehicle.recordId}, '${vehicle.licensePlate}')">
                    <i class="bi bi-gear"></i> 操作
                </button>
            </td>
        `;
        tableBody.appendChild(row);
    });
}

function displayVehicleHistory(vehicles) {
    const tableBody = document.getElementById('history-vehicles-body');
    tableBody.innerHTML = '';
    
    vehicles.forEach(vehicle => {
        const entryTime = new Date(vehicle.entryTime);
        const exitTime = vehicle.exitTime ? new Date(vehicle.exitTime) : null;
        const duration = vehicle.durationMinutes ? formatDuration(vehicle.durationMinutes) : '-';
        
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="fw-semibold">${vehicle.licensePlate}</td>
            <td>${entryTime.toLocaleString()}</td>
            <td>${exitTime ? exitTime.toLocaleString() : '仍在場內'}</td>
            <td>${duration}</td>
            <td>$${vehicle.totalFee || 0}</td>
        `;
        tableBody.appendChild(row);
    });
}

function getPaymentStatusBadge(status) {
    switch (status) {
        case 'Paid':
            return '<span class="badge badge-success">已繳費</span>';
        case 'Unpaid':
            return '<span class="badge badge-danger">未繳費</span>';
        case 'Payment Expired':
            return '<span class="badge badge-warning">逾期</span>';
        default:
            return '<span class="badge badge-secondary">未知</span>';
    }
}

function formatDuration(minutes) {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;
}

function openManualAction(recordId, licensePlate) {
    document.getElementById('manual-record-id').value = recordId;
    document.getElementById('manual-license-plate').value = licensePlate;
    document.getElementById('manual-action').value = '';
    document.getElementById('manual-amount').value = '';
    document.getElementById('amount-group').style.display = 'none';
    
    const modal = new bootstrap.Modal(document.getElementById('manualActionModal'));
    modal.show();
}

async function executeManualAction() {
    const recordId = document.getElementById('manual-record-id').value;
    const action = document.getElementById('manual-action').value;
    const amount = document.getElementById('manual-amount').value;
    
    if (!action) {
        alert('請選擇操作類型');
        return;
    }
    
    const payload = { action };
    if (action === 'mark_paid' && amount) {
        payload.amount = parseInt(amount);
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/admin/records/${recordId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify(payload)
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            alert('操作成功執行');
            bootstrap.Modal.getInstance(document.getElementById('manualActionModal')).hide();
            loadVehicles(); // Refresh vehicle list
        } else {
            alert(data.error || '操作失敗');
        }
    } catch (error) {
        alert('操作失敗，請稍後再試');
        console.error('Manual action error:', error);
    }
}

function loadReportsPage() {
    // Already loaded in loadVehiclesPage for lot selector
}

async function generateReport() {
    const lotId = document.getElementById('report-lot').value;
    const startDate = document.getElementById('report-start-date').value;
    const endDate = document.getElementById('report-end-date').value;
    
    if (!startDate || !endDate) {
        alert('請選擇開始和結束日期');
        return;
    }
    
    try {
        let url = `${API_BASE_URL}/api/v1/admin/reports/revenue?start_date=${startDate}&end_date=${endDate}`;
        if (lotId) {
            url += `&lot_id=${lotId}`;
        }
        
        const response = await fetch(url, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            displayReportResults(data);
        } else {
            alert('報表產生失敗');
        }
    } catch (error) {
        alert('報表產生失敗，請稍後再試');
        console.error('Report generation error:', error);
    }
}

function displayReportResults(data) {
    document.getElementById('total-revenue-amount').textContent = data.totalRevenue.toLocaleString();
    
    const tableBody = document.getElementById('report-table-body');
    tableBody.innerHTML = '';
    
    data.reports.forEach(report => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="fw-semibold">${report.lotName}</td>
            <td>${report.totalTransactions}</td>
            <td>${report.completedParking}</td>
            <td>$${report.totalRevenue.toLocaleString()}</td>
            <td>$${report.averageRevenue.toLocaleString()}</td>
        `;
        tableBody.appendChild(row);
    });
    
    document.getElementById('report-results').style.display = 'block';
}

function viewLotDetails(lotId) {
    // Switch to vehicles page and select the lot
    showPage('vehicles');
    document.querySelector('.nav-link[data-page="vehicles"]').classList.add('active');
    document.querySelector('.nav-link[data-page="lots"]').classList.remove('active');
    
    // Set lot selector and load vehicles
    setTimeout(() => {
        document.getElementById('lot-selector').value = lotId;
        loadVehicles();
    }, 100);
}

// Utility functions
function formatCurrency(amount) {
    return new Intl.NumberFormat('zh-TW', {
        style: 'currency',
        currency: 'TWD'
    }).format(amount);
}

function formatDateTime(dateString) {
    return new Date(dateString).toLocaleString('zh-TW');
}

// Error handling
window.addEventListener('unhandledrejection', function(event) {
    console.error('Unhandled promise rejection:', event.reason);
    // Could show a user-friendly error message here
});

// Auto-refresh dashboard every 30 seconds when on dashboard page
setInterval(() => {
    const dashboardPage = document.getElementById('dashboard-page');
    if (dashboardPage && dashboardPage.style.display !== 'none') {
        loadDashboard();
    }
}, 30000);

// ============= 管理員管理功能 =============

async function loadAdminsPage() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/admin/admins`);
        const data = await response.json();
        
        if (response.ok) {
            displayAdmins(data);
        } else {
            console.error('Failed to load admins:', response.status, data.error);
            if (response.status === 401) {
                showAlert('需要重新登入', 'warning');
                // Redirect to login or show login modal
                window.location.reload();
            } else if (response.status === 403) {
                showAlert('需要超級管理員權限才能存取此功能', 'warning');
            } else {
                showAlert(`載入管理員清單失敗: ${data.error}`, 'danger');
            }
        }
    } catch (error) {
        console.error('Error loading admins:', error);
        showAlert('系統錯誤，請稍後再試', 'danger');
    }
}

function displayAdmins(admins) {
    const tbody = document.getElementById('admins-table-body');
    
    if (admins.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">暫無管理員資料</td></tr>';
        return;
    }
    
    tbody.innerHTML = admins.map(admin => {
        const roleText = admin.RoleLevel === 99 ? 
            '<span class="badge bg-danger">超級管理員</span>' : 
            '<span class="badge bg-primary">一般管理員</span>';
            
        const lotNames = admin.lots && admin.lots.length > 0 ? 
            admin.lots.map(lot => lot.Name).join(', ') : 
            (admin.RoleLevel === 99 ? '所有停車場' : '無');
            
        const lastLogin = admin.LastLoginTime ? 
            formatDateTime(admin.LastLoginTime) : '從未登入';
            
        return `
            <tr>
                <td>${admin.Username}</td>
                <td>${roleText}</td>
                <td title="${lotNames}">${lotNames.length > 30 ? lotNames.substring(0, 30) + '...' : lotNames}</td>
                <td>${lastLogin}</td>
                <td>${formatDateTime(admin.CreatedAt)}</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" onclick="editAdmin(${admin.AdminID})">
                        <i class="bi bi-pencil"></i>編輯
                    </button>
                    ${admin.Username !== currentAdmin.Username ? 
                        `<button class="btn btn-sm btn-outline-danger" onclick="deleteAdmin(${admin.AdminID}, '${admin.Username}')">
                            <i class="bi bi-trash"></i>刪除
                        </button>` : 
                        '<span class="text-muted small">目前用戶</span>'
                    }
                </td>
            </tr>
        `;
    }).join('');
}

async function openAdminModal(adminId = null) {
    const title = document.getElementById('adminModalTitle');
    const form = document.getElementById('admin-form');
    const passwordGroup = document.getElementById('password-group');
    const saveText = document.getElementById('save-admin-text');
    
    // Reset form and clear previous values
    form.reset();
    document.getElementById('admin-id').value = adminId || '';
    
    // Clean up any existing backdrop issues
    document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
        backdrop.remove();
    });
    document.body.classList.remove('modal-open');
    document.body.style.overflow = '';
    document.body.style.paddingRight = '';
    
    if (adminId) {
        title.textContent = '編輯管理員';
        passwordGroup.style.display = 'none';
        document.getElementById('admin-password').required = false;
        saveText.textContent = '更新';
    } else {
        title.textContent = '新增管理員';
        passwordGroup.style.display = 'block';
        document.getElementById('admin-password').required = true;
        saveText.textContent = '新增';
    }
    
    // 先載入停車場資料
    await loadParkingLotsForModal();
    
    // 如果是編輯模式，載入管理員資料
    if (adminId) {
        await loadAdminData(adminId);
    } else {
        // For new admin, set default role and update visibility
        document.getElementById('admin-role-level').value = '1';
        updateLotAssignmentsVisibility();
    }
    
    // 資料載入完成後顯示模態框
    const modalElement = document.getElementById('adminModal');
    const modal = new bootstrap.Modal(modalElement, {
        backdrop: 'static',
        keyboard: false
    });
    modal.show();
}

async function loadAdminData(adminId) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/admin/admins/${adminId}`);
        const data = await response.json();
        
        if (response.ok && data) {
            // Set form values with proper field names and force UI update
            const usernameField = document.getElementById('admin-username');
            const roleField = document.getElementById('admin-role-level');
            
            if (usernameField && data.Username) {
                usernameField.value = data.Username;
                // Force visual update by triggering input events
                usernameField.dispatchEvent(new Event('input', { bubbles: true }));
                usernameField.dispatchEvent(new Event('change', { bubbles: true }));
                // Also set the attribute for consistency
                usernameField.setAttribute('value', data.Username);
                console.log(`Set username field to: ${data.Username}`);
            }
            if (roleField && data.RoleLevel) {
                roleField.value = data.RoleLevel;
                roleField.dispatchEvent(new Event('change', { bubbles: true }));
            }
            
            // Load assigned parking lots
            if (data.lots && Array.isArray(data.lots)) {
                const assignedLotIds = data.lots.map(lot => lot.ParkingLotID);
                document.querySelectorAll('#lot-checkboxes input[type="checkbox"]').forEach(checkbox => {
                    checkbox.checked = assignedLotIds.includes(parseInt(checkbox.value));
                });
            }
            
            updateLotAssignmentsVisibility();
        } else {
            console.error('Failed to load admin data:', response.status, data);
            showAlert(data?.error || '載入管理員資料失敗', 'danger');
        }
    } catch (error) {
        console.error('Error loading admin data:', error);
        showAlert('系統錯誤，請稍後再試', 'danger');
    }
}

async function loadParkingLotsForModal() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/admin/lots`);
        const data = await response.json();
        
        if (response.ok) {
            const container = document.getElementById('lot-checkboxes');
            // Handle both data.lots and direct data array formats
            const lots = Array.isArray(data) ? data : (data.lots || []);
            container.innerHTML = lots.map(lot => `
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" value="${lot.ParkingLotID}" id="lot-${lot.ParkingLotID}">
                    <label class="form-check-label" for="lot-${lot.ParkingLotID}">
                        ${lot.Name}
                    </label>
                </div>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading parking lots for modal:', error);
    }
}

async function saveAdmin() {
    const adminId = document.getElementById('admin-id').value;
    const isEdit = adminId !== '';
    
    // Validate required fields
    const username = document.getElementById('admin-username').value?.trim();
    const roleLevel = document.getElementById('admin-role-level').value;
    const password = document.getElementById('admin-password').value;
    
    if (!username) {
        showAlert('使用者名稱為必填', 'danger');
        return;
    }
    
    if (!roleLevel) {
        showAlert('角色等級為必填', 'danger');
        return;
    }
    
    if (!isEdit && !password) {
        showAlert('新增管理員時密碼為必填', 'danger');
        return;
    }
    
    const formData = {
        Username: username,
        RoleLevel: parseInt(roleLevel),
        lots: []
    };
    
    // Add password for new admin
    if (!isEdit && password) {
        formData.Password = password;
    }
    
    // Get selected parking lots
    const selectedLots = [];
    document.querySelectorAll('#lot-checkboxes input[type="checkbox"]:checked').forEach(checkbox => {
        selectedLots.push(parseInt(checkbox.value));
    });
    formData.lots = selectedLots;
    
    try {
        const url = isEdit ? 
            `${API_BASE_URL}/api/v1/admin/admins/${adminId}` : 
            `${API_BASE_URL}/api/v1/admin/admins`;
            
        const method = isEdit ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showAlert(isEdit ? '管理員更新成功' : '管理員新增成功', 'success');
            // Properly close modal and clean up
            const modalElement = document.getElementById('adminModal');
            const modal = bootstrap.Modal.getInstance(modalElement);
            if (modal) {
                modal.hide();
            }
            // Clean up any remaining backdrop
            setTimeout(() => {
                document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
                    backdrop.remove();
                });
                document.body.classList.remove('modal-open');
                document.body.style.overflow = '';
                document.body.style.paddingRight = '';
            }, 300);
            loadAdminsPage();
        } else {
            showAlert(data.error || '操作失敗', 'danger');
        }
    } catch (error) {
        console.error('Error saving admin:', error);
        showAlert('系統錯誤，請稍後再試', 'danger');
    }
}

async function editAdmin(adminId) {
    await openAdminModal(adminId);
}

async function deleteAdmin(adminId, username) {
    if (!confirm(`確定要刪除管理員 "${username}" 嗎？此操作無法復原。`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/admin/admins/${adminId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showAlert('管理員刪除成功', 'success');
            loadAdminsPage();
        } else {
            const data = await response.json();
            showAlert(data.error || '刪除失敗', 'danger');
        }
    } catch (error) {
        console.error('Error deleting admin:', error);
        showAlert('系統錯誤，請稍後再試', 'danger');
    }
}

function updateLotAssignmentsVisibility() {
    const roleLevel = document.getElementById('admin-role-level').value;
    const lotGroup = document.getElementById('lot-assignments-group');
    
    if (roleLevel === '99') {
        // SuperAdmin doesn't need lot assignments
        lotGroup.style.display = 'none';
    } else {
        lotGroup.style.display = 'block';
    }
}

// Add event listener for role level change
document.addEventListener('DOMContentLoaded', function() {
    const roleSelect = document.getElementById('admin-role-level');
    if (roleSelect) {
        roleSelect.addEventListener('change', updateLotAssignmentsVisibility);
    }
});

function showAlert(message, type = 'info') {
    // Create alert element
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 1060; max-width: 400px;';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}