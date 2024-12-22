document.addEventListener('DOMContentLoaded', () => {
    const transactionsTable = document.getElementById('transactions');
    const form = document.getElementById('transaction-form');
    const logoutButton = document.getElementById('logout-button');

    async function loadTransactions() {
        const response = await fetch('/api/transactions');
        if (response.ok) {
            const transactions = await response.json();
            updateTransactionTable(transactions);
        } else {
            alert('Failed to load transactions. Redirecting to login.');
            window.location.href = 'login.html';
        }
    }

    function updateTransactionTable(transactions) {
        transactionsTable.innerHTML = '';
        transactions.forEach(({ description, amount, date, category }) => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${description}</td>
                <td>${amount}</td>
                <td>${date}</td>
                <td>${category}</td>
            `;
            transactionsTable.appendChild(row);
        });
    }

    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        const formData = new FormData(form);

        const response = await fetch('/api/add_transaction', {
            method: 'POST',
            body: new URLSearchParams(formData)
        });

        if (response.ok) {
            form.reset();
            loadTransactions();
        } else {
            alert('Failed to add transaction.');
        }
    });

    logoutButton.addEventListener('click', async () => {
        await fetch('/api/logout');
        window.location.href = 'login.html';
    });

    loadTransactions();
});
