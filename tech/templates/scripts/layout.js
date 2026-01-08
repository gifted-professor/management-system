/**
 * Layout Adaptation Script
 * 布局适配脚本 - 角色切换、视图控制
 *
 * NOTE: This file will contain layout-related JavaScript
 * For now, it serves as a placeholder.
 */

// Role switching logic
function switchTopRole(role) {
    const btnService = document.getElementById('topRoleService');
    const btnOps = document.getElementById('topRoleOps');

    const activeClass = "bg-white text-brand-600 shadow-sm";
    const inactiveClass = "text-slate-500 hover:text-slate-700 bg-transparent shadow-none";

    if (role === 'customer-service') {
        btnService.className = `px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${activeClass}`;
        btnOps.className = `px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${inactiveClass}`;
        const radio = document.getElementById('roleCustomerService');
        if (radio) radio.click();
    } else {
        btnService.className = `px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${inactiveClass}`;
        btnOps.className = `px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${activeClass}`;
        const radio = document.getElementById('roleOperations');
        if (radio) radio.click();
    }
}

console.log('Layout adaptation loaded');
