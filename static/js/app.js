document.addEventListener('DOMContentLoaded', function() {
    // Enable Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Enable Bootstrap popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Function to show toast notifications
    function showToastNotification(title, message, link = null) {
        const toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) return;
        
        const now = new Date();
        const timeStr = now.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        
        // Create toast element
        const toastEl = document.createElement('div');
        toastEl.className = 'toast';
        toastEl.setAttribute('role', 'alert');
        toastEl.setAttribute('aria-live', 'assertive');
        toastEl.setAttribute('aria-atomic', 'true');
        
        // Create toast content
        let toastContent = `
            <div class="toast-header">
                <i class="fas fa-bell me-2 text-primary"></i>
                <strong class="me-auto">${title}</strong>
                <small>${timeStr}</small>
                <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                ${message}
        `;
        
        // Add link button if provided
        if (link) {
            toastContent += `
                <div class="mt-2">
                    <a href="${link}" class="btn btn-sm btn-primary">View</a>
                </div>
            `;
        }
        
        toastContent += `</div>`;
        toastEl.innerHTML = toastContent;
        
        // Add to container
        toastContainer.appendChild(toastEl);
        
        // Initialize and show toast
        const toast = new bootstrap.Toast(toastEl, {
            autohide: true,
            delay: 5000
        });
        toast.show();
        
        // Remove from DOM after hidden
        toastEl.addEventListener('hidden.bs.toast', function() {
            toastEl.remove();
        });
    }
    
    // Check for new notifications via API every 30 seconds
    function checkForNewNotifications() {
        fetch('/api/notifications/unread')
            .then(response => response.json())
            .then(data => {
                if (data.notifications && data.notifications.length > 0) {
                    data.notifications.forEach(notification => {
                        showToastNotification(
                            notification.title,
                            notification.message,
                            notification.link
                        );
                    });
                }
            })
            .catch(error => console.error('Error checking notifications:', error));
    }
    
    // Show any initial unread notifications passed from server
    const notificationsData = window.notificationsData || [];
    if (notificationsData.length > 0) {
        notificationsData.forEach(notification => {
            showToastNotification(
                notification.title,
                notification.message,
                notification.link
            );
        });
    }
    
    // Set interval to check for new notifications
    // setInterval(checkForNewNotifications, 30000);
    
    // Handle currency conversion in add expense form
    const currencySelect = document.getElementById('currency');
    const amountInput = document.getElementById('amount');
    const convertedAmountDisplay = document.getElementById('converted-amount');
    
    if (currencySelect && amountInput && convertedAmountDisplay) {
        let exchangeRates = {};
        
        // Fetch exchange rates
        fetch('/api/exchange-rates')
            .then(response => response.json())
            .then(rates => {
                exchangeRates = rates;
                updateConvertedAmount();
            })
            .catch(error => console.error('Error fetching exchange rates:', error));
        
        function updateConvertedAmount() {
            const amount = parseFloat(amountInput.value) || 0;
            const currency = currencySelect.value;
            const rate = exchangeRates[currency] || 1;
            
            const usdAmount = amount / rate;
            convertedAmountDisplay.textContent = `≈ $${usdAmount.toFixed(2)} USD`;
        }
        
        amountInput.addEventListener('input', updateConvertedAmount);
        currencySelect.addEventListener('change', updateConvertedAmount);
    }
    
    // Handle split type selection in add expense form
    const splitTypeRadios = document.querySelectorAll('input[name="split_type"]');
    const customSplitSection = document.getElementById('custom-split-section');
    
    if (splitTypeRadios.length && customSplitSection) {
        splitTypeRadios.forEach(radio => {
            radio.addEventListener('change', function() {
                if (this.value === 'custom') {
                    customSplitSection.classList.remove('d-none');
                } else {
                    customSplitSection.classList.add('d-none');
                }
            });
        });
    }
    
    // Handle participant selection and custom split percentages
    const participantsSelect = document.getElementById('participants');
    const customSplitContainer = document.getElementById('custom-split-container');
    
    if (participantsSelect && customSplitContainer) {
        participantsSelect.addEventListener('change', function() {
            updateCustomSplitFields();
        });
        
        function updateCustomSplitFields() {
            customSplitContainer.innerHTML = '';
            
            const selectedOptions = Array.from(participantsSelect.selectedOptions);
            if (selectedOptions.length === 0) return;
            
            // Default percentage per participant
            const defaultPercentage = (100 / selectedOptions.length).toFixed(2);
            
            selectedOptions.forEach(option => {
                const userId = option.value;
                const userName = option.text;
                
                const formGroup = document.createElement('div');
                formGroup.className = 'mb-3';
                
                formGroup.innerHTML = `
                    <label for="split_${userId}" class="form-label">${userName} (%)</label>
                    <input type="number" class="form-control custom-split-input" 
                           id="split_${userId}" name="split_${userId}" 
                           value="${defaultPercentage}" min="0" max="100" step="0.01">
                `;
                
                customSplitContainer.appendChild(formGroup);
            });
            
            // Add event listeners for percentage inputs
            const splitInputs = document.querySelectorAll('.custom-split-input');
            splitInputs.forEach(input => {
                input.addEventListener('input', function() {
                    validateTotalPercentage(splitInputs);
                });
            });
        }
        
        function validateTotalPercentage(inputs) {
            let total = 0;
            inputs.forEach(input => {
                total += parseFloat(input.value) || 0;
            });
            
            const totalDisplay = document.getElementById('total-percentage');
            if (totalDisplay) {
                totalDisplay.textContent = total.toFixed(2);
                
                if (Math.abs(total - 100) < 0.01) {
                    totalDisplay.classList.remove('text-danger');
                    totalDisplay.classList.add('text-success');
                } else {
                    totalDisplay.classList.remove('text-success');
                    totalDisplay.classList.add('text-danger');
                }
            }
        }
    }
    
    // Handle form submission validation
    const expenseForm = document.getElementById('expense-form');
    if (expenseForm) {
        expenseForm.addEventListener('submit', function(event) {
            const splitType = document.querySelector('input[name="split_type"]:checked').value;
            
            if (splitType === 'custom') {
                const totalDisplay = document.getElementById('total-percentage');
                const total = parseFloat(totalDisplay.textContent);
                
                if (Math.abs(total - 100) >= 0.01) {
                    event.preventDefault();
                    alert('Custom split percentages must add up to 100%');
                }
            }
        });
    }
    
    // Copy invite code to clipboard
    const copyInviteCodeBtn = document.getElementById('copy-invite-code');
    if (copyInviteCodeBtn) {
        copyInviteCodeBtn.addEventListener('click', function() {
            const inviteCode = this.getAttribute('data-code');
            
            navigator.clipboard.writeText(inviteCode).then(() => {
                // Show success tooltip
                const tooltip = bootstrap.Tooltip.getInstance(copyInviteCodeBtn);
                copyInviteCodeBtn.setAttribute('data-bs-original-title', 'Copied!');
                tooltip.show();
                
                // Reset tooltip after 2 seconds
                setTimeout(() => {
                    copyInviteCodeBtn.setAttribute('data-bs-original-title', 'Copy to clipboard');
                }, 2000);
            }).catch(err => {
                console.error('Failed to copy: ', err);
            });
        });
    }
});
