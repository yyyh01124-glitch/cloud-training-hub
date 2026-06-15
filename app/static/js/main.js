// Auto-dismiss flash messages after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(function() {
        document.querySelectorAll('.alert-dismissible').forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
});

// Confirm dialog for destructive actions
function confirmAction(message) {
    return confirm(message || '确认执行此操作？');
}
