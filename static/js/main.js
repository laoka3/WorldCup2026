/*
 * 世界杯足球数据分析Agent - 公共JavaScript
 * 提供全局通用功能
 */

document.addEventListener('DOMContentLoaded', function() {
    initSmoothScroll();
    initImageFallback();
});

function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            const target = document.querySelector(targetId);
            if (target) {
                e.preventDefault();
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });
}

function initImageFallback() {
    document.querySelectorAll('img').forEach(img => {
        img.addEventListener('error', function() {
            this.style.display = 'none';
            const parent = this.parentElement;
            if (parent && !parent.querySelector('.img-fallback')) {
                const fallback = document.createElement('div');
                fallback.className = 'img-fallback w-full h-full flex items-center justify-center bg-wc-green-dark';
                fallback.innerHTML = '<i class="fas fa-futbol text-4xl text-wc-gold/30"></i>';
                parent.appendChild(fallback);
            }
        });
    });
}
