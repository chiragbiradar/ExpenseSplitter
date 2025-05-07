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
                                        const balance = data.balances[userName];
                                        return balance >= 0 
                                            ? `${userName} is owed $${balance.toFixed(2)}` 
                                            : `${userName} owes $${Math.abs(balance).toFixed(2)}`;
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
                        const balance = data.balances[userName];
                        const balanceItem = document.createElement('div');
                        balanceItem.className = 'mb-2';
                        
                        if (balance > 0) {
                            balanceItem.innerHTML = `
                                <span class="fw-bold">${userName}:</span> 
                                <span class="text-success">is owed $${balance.toFixed(2)}</span>
                            `;
                        } else if (balance < 0) {
                            balanceItem.innerHTML = `
                                <span class="fw-bold">${userName}:</span> 
                                <span class="text-danger">owes $${Math.abs(balance).toFixed(2)}</span>
                            `;
                        } else {
                            balanceItem.innerHTML = `
                                <span class="fw-bold">${userName}:</span> 
                                <span class="text-secondary">is settled</span>
                            `;
                        }
                        
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
                                        const balance = data.balances[userName];
                                        const percentage = (context.raw / context.chart.getDatasetMeta(0).total * 100).toFixed(1);
                                        return balance >= 0 
                                            ? `${userName}: $${Math.abs(balance).toFixed(2)} (${percentage}%)` 
                                            : `${userName}: $${Math.abs(balance).toFixed(2)} (${percentage}%)`;
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
