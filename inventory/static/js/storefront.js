
function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    const color = type === 'success' ? '#2ecc71' : '#e74c3c';
    const bgColor = '#4b2e1e';
    
    toast.style.cssText = `
        position: fixed;
        bottom: 30px;
        right: 30px;
        background: ${bgColor};
        color: white;
        padding: 16px 28px;
        border-radius: 12px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        z-index: 10000;
        font-family: 'Italiana', serif;
        display: flex;
        align-items: center;
        gap: 12px;
        transform: translateX(120%);
        transition: transform 0.5s cubic-bezier(0.68, -0.55, 0.265, 1.55);
    `;
    
    const icon = type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle';
    toast.innerHTML = `<i class="fas ${icon}" style="color: ${color}; font-size: 20px;"></i> 
                       <span style="font-weight: 500; letter-spacing: 0.5px;">${message}</span>`;
    
    document.body.appendChild(toast);
    
    // Force reflow
    toast.offsetHeight;
    
    // Slide in
    toast.style.transform = 'translateX(0)';
    
    // Remove after delay
    setTimeout(() => {
        toast.style.transform = 'translateX(120%)';
        setTimeout(() => toast.remove(), 500);
    }, 4000);
}

function updateCartBadgeGlobal() {
    const cart = JSON.parse(localStorage.getItem('cart')) || {};
    const totalItems = Object.values(cart).reduce((a, b) => a + b, 0);
    const badge = document.getElementById('cart-count-global');
    if (badge) {
        badge.textContent = totalItems;
        badge.style.display = totalItems > 0 ? 'flex' : 'none';
    }
}

document.addEventListener('DOMContentLoaded', updateCartBadgeGlobal);
