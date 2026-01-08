/**
 * Tablesort - Lightweight table sorting library
 * 表格排序库
 */
(function () {
    function getSortValue(cell, method) {
        if (!cell) {
            return method === 'number' ? -Infinity : '';
        }
        const attr = cell.getAttribute('data-sort-value');
        if (method === 'number') {
            const raw = attr !== null ? attr : cell.textContent || '';
            const parsed = parseFloat(raw);
            return Number.isFinite(parsed) ? parsed : -Infinity;
        }
        return (attr !== null ? attr : cell.textContent || '').trim().toLowerCase();
    }

    function Tablesort(table) {
        if (!table) {
            throw new Error('Tablesort requires a table element.');
        }
        this.table = table;
        this.thead = table.querySelector('thead');
        this.headers = this.thead ? Array.from(this.thead.querySelectorAll('th')) : [];
        this.tbody = table.tBodies[0];
        this.init();
    }

    Tablesort.prototype.init = function () {
        const self = this;
        this.headers.forEach(function (header, index) {
            if (header.classList.contains('no-sort')) {
                return;
            }
            header.addEventListener('click', function () {
                self.sortBy(index, header);
            });
        });
    };

    Tablesort.prototype.sortBy = function (index, header) {
        if (!this.tbody) {
            return;
        }
        const method = header.getAttribute('data-sort-method') || undefined;

        // 只对可见行进行排序（排除display:none的行）
        const allRows = Array.from(this.tbody.rows);
        const visibleRows = allRows.filter(row => row.style.display !== 'none');
        const hiddenRows = allRows.filter(row => row.style.display === 'none');
        const currentOrder = header.getAttribute('data-sort-order') || 'asc';
        const newOrder = currentOrder === 'asc' ? 'desc' : 'asc';

        this.headers.forEach(function (head) {
            if (head !== header) {
                head.removeAttribute('data-sort-order');
            }
        });

        visibleRows.sort(function (a, b) {
            const aVal = getSortValue(a.cells[index], method);
            const bVal = getSortValue(b.cells[index], method);
            if (method === 'number') {
                return aVal - bVal;
            }
            if (aVal === bVal) {
                return 0;
            }
            return aVal > bVal ? 1 : -1;
        });

        if (newOrder === 'desc') {
            visibleRows.reverse();
        }

        // 先添加可见行，再添加隐藏行（保持隐藏行在最后）
        const fragment = document.createDocumentFragment();
        visibleRows.forEach(function (row) {
            fragment.appendChild(row);
        });
        hiddenRows.forEach(function (row) {
            fragment.appendChild(row);
        });
        this.tbody.appendChild(fragment);
        header.setAttribute('data-sort-order', newOrder);
    };

    window.Tablesort = Tablesort;
})();

// Initialize all tables on page load
document.addEventListener('DOMContentLoaded', function() {
    try {
        const allTables = Array.from(document.querySelectorAll('table'));
        allTables.forEach(t => {
            try {
                new Tablesort(t);
            } catch (e) {
                console.warn('Failed to initialize table sort:', e);
            }
        });

        // Click priority header to sort by default
        const mainTable = document.getElementById('actionTable');
        if (mainTable) {
            const priorityHeader = mainTable.querySelector('th:nth-child(2)');
            if (priorityHeader) {
                priorityHeader.click();
            }
        }
    } catch (err) {
        console.warn('Tablesort initialization failed', err);
    }
});
