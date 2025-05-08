document.addEventListener('DOMContentLoaded', function() {
    // Balance chart for group page
    const balanceChartCanvas = document.getElementById('balance-chart');
    if (balanceChartCanvas) {
        const groupId = balanceChartCanvas.getAttribute('data-group-id');

        // Fetch balance data
        fetch(`/api/groups/${groupId}/balance-data`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    console.error('Error fetching balance data:', data.error);
                    return;
                }

                // Create chart
                const balanceChart = new Chart(balanceChartCanvas, {
                    type: 'bar',
                    data: {
                        labels: data.labels,
                        datasets: data.datasets
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                display: false
                            },
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        const userName = context.label;
                                        const userBalances = data.balances[userName];
                                        const displayCurrency = data.display_currency;

                                        if (displayCurrency) {
                                            // Single currency format
                                            const amount = userBalances;
                                            const formattedAmount = Math.abs(amount).toFixed(2);

                                            if (amount > 0) {
                                                return `${userName} is owed ${displayCurrency} ${formattedAmount}`;
                                            } else if (amount < 0) {
                                                return `${userName} owes ${displayCurrency} ${formattedAmount}`;
                                            } else {
                                                return `${userName} is settled`;
                                            }
                                        } else {
                                            // Multi-currency format
                                            const balanceLines = [];
                                            for (const currency in userBalances) {
                                                const amount = userBalances[currency];
                                                if (amount !== 0) {
                                                    const formattedAmount = Math.abs(amount).toFixed(2);
                                                    if (amount > 0) {
                                                        balanceLines.push(`is owed ${currency} ${formattedAmount}`);
                                                    } else {
                                                        balanceLines.push(`owes ${currency} ${formattedAmount}`);
                                                    }
                                                }
                                            }

                                            return balanceLines.length > 0
                                                ? [`${userName}:`, ...balanceLines]
                                                : `${userName} is settled`;
                                        }
                                    }
                                }
                            }
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                title: {
                                    display: true,
                                    text: 'Amount'
                                }
                            },
                            x: {
                                title: {
                                    display: true,
                                    text: 'Group Members'
                                }
                            }
                        }
                    }
                });

                // Update balance summary in the DOM
                const balanceSummary = document.getElementById('balance-summary');
                if (balanceSummary) {
                    balanceSummary.innerHTML = '';

                    for (const userName in data.balances) {
                        const userBalances = data.balances[userName];
                        const displayCurrency = data.display_currency;
                        const balanceItem = document.createElement('div');
                        balanceItem.className = 'mb-2';

                        // Create HTML for the user's name
                        let balanceHTML = `<span class="fw-bold">${userName}:</span>`;

                        if (displayCurrency) {
                            // Single currency format
                            const amount = userBalances;
                            if (amount !== 0) {
                                const formattedAmount = Math.abs(amount).toFixed(2);
                                if (amount > 0) {
                                    balanceHTML += ` <span class="text-success">is owed ${displayCurrency} ${formattedAmount}</span>`;
                                } else {
                                    balanceHTML += ` <span class="text-danger">owes ${displayCurrency} ${formattedAmount}</span>`;
                                }
                            } else {
                                balanceHTML += ` <span class="text-secondary">is settled</span>`;
                            }
                        } else {
                            // Multi-currency format
                            // Check if user has any non-zero balances
                            const hasBalances = Object.values(userBalances).some(amount => amount !== 0);

                            if (hasBalances) {
                                balanceHTML += '<ul class="list-unstyled ms-3 mb-0">';

                                // Add each currency balance
                                for (const currency in userBalances) {
                                    const amount = userBalances[currency];
                                    if (amount !== 0) {
                                        const formattedAmount = Math.abs(amount).toFixed(2);
                                        if (amount > 0) {
                                            balanceHTML += `<li><span class="text-success">is owed ${currency} ${formattedAmount}</span></li>`;
                                        } else {
                                            balanceHTML += `<li><span class="text-danger">owes ${currency} ${formattedAmount}</span></li>`;
                                        }
                                    }
                                }

                                balanceHTML += '</ul>';
                            } else {
                                balanceHTML += ` <span class="text-secondary">is settled</span>`;
                            }
                        }

                        balanceItem.innerHTML = balanceHTML;
                        balanceSummary.appendChild(balanceItem);
                    }
                }
            })
            .catch(error => console.error('Error fetching balance data:', error));
    }

    // Expense breakdown chart for settlements page
    const expenseChartCanvas = document.getElementById('expense-breakdown-chart');
    if (expenseChartCanvas) {
        const groupId = expenseChartCanvas.getAttribute('data-group-id');

        // Fetch balance data (reusing the same endpoint)
        fetch(`/api/groups/${groupId}/balance-data`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    console.error('Error fetching balance data:', data.error);
                    return;
                }

                // Create pie chart for expense breakdown
                const expenseChart = new Chart(expenseChartCanvas, {
                    type: 'pie',
                    data: {
                        labels: data.labels,
                        datasets: [{
                            data: data.datasets[0].data,
                            backgroundColor: data.datasets[0].backgroundColor,
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                position: 'right'
                            },
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        const userName = context.label;
                                        const userBalances = data.balances[userName];
                                        const displayCurrency = data.display_currency;
                                        const percentage = (context.raw / context.chart.getDatasetMeta(0).total * 100).toFixed(1);

                                        if (displayCurrency) {
                                            // Single currency format
                                            const amount = userBalances;
                                            const formattedAmount = Math.abs(amount).toFixed(2);

                                            if (amount > 0) {
                                                return `${userName} (${percentage}%): is owed ${displayCurrency} ${formattedAmount}`;
                                            } else if (amount < 0) {
                                                return `${userName} (${percentage}%): owes ${displayCurrency} ${formattedAmount}`;
                                            } else {
                                                return `${userName} (${percentage}%): is settled`;
                                            }
                                        } else {
                                            // Multi-currency format
                                            const balanceLines = [`${userName} (${percentage}%):`];
                                            for (const currency in userBalances) {
                                                const amount = userBalances[currency];
                                                if (amount !== 0) {
                                                    const formattedAmount = Math.abs(amount).toFixed(2);
                                                    if (amount > 0) {
                                                        balanceLines.push(`is owed ${currency} ${formattedAmount}`);
                                                    } else {
                                                        balanceLines.push(`owes ${currency} ${formattedAmount}`);
                                                    }
                                                }
                                            }

                                            return balanceLines;
                                        }
                                    }
                                }
                            }
                        }
                    }
                });
            })
            .catch(error => console.error('Error fetching expense data:', error));
    }
});
