// Kryptacode — interações de UI (menu mobile, sidebar do painel, reveals)
document.addEventListener('DOMContentLoaded', () => {

  // ---------- Menu mobile do site público ----------
  const navToggle = document.querySelector('.nav-toggle');
  const navLinks = document.querySelector('.nav-links');
  if (navToggle && navLinks) {
    navToggle.addEventListener('click', () => {
      const isOpen = navLinks.classList.toggle('open');
      navToggle.classList.toggle('open', isOpen);
      navToggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
      document.body.style.overflow = isOpen ? 'hidden' : '';
    });

    navLinks.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => {
        navLinks.classList.remove('open');
        navToggle.classList.remove('open');
        document.body.style.overflow = '';
      });
    });
  }

  // ---------- Gaveta lateral do painel (mobile/tablet) ----------
  const sidebar = document.querySelector('.dash-sidebar');
  const sidebarToggle = document.querySelector('.dash-topbar .sidebar-toggle');
  const overlay = document.querySelector('.sidebar-overlay');

  function closeSidebar() {
    if (sidebar) sidebar.classList.remove('open');
    if (overlay) overlay.classList.remove('open');
    document.body.style.overflow = '';
  }

  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener('click', () => {
      sidebar.classList.add('open');
      if (overlay) overlay.classList.add('open');
      document.body.style.overflow = 'hidden';
    });
  }
  if (overlay) overlay.addEventListener('click', closeSidebar);

  // fecha a gaveta se a tela for redimensionada pra desktop
  window.addEventListener('resize', () => {
    if (window.innerWidth > 900) closeSidebar();
  });

  // ---------- Reveal suave ao rolar a página ----------
  const revealEls = document.querySelectorAll('.reveal');
  if (revealEls.length && 'IntersectionObserver' in window) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('in-view');
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.15, rootMargin: '0px 0px -40px 0px' });
    revealEls.forEach(el => io.observe(el));
  } else {
    revealEls.forEach(el => el.classList.add('in-view'));
  }

  // ---------- Contador animado (números da seção de destaque) ----------
  const counters = document.querySelectorAll('[data-count]');
  if (counters.length && 'IntersectionObserver' in window) {
    const countIO = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        const el = entry.target;
        const raw = el.getAttribute('data-count');
        const match = raw.match(/^(\d+)(.*)$/);
        if (!match) return;
        const target = parseInt(match[1], 10);
        const suffix = match[2] || '';
        const duration = 900;
        const start = performance.now();

        function tick(now) {
          const progress = Math.min((now - start) / duration, 1);
          const eased = 1 - Math.pow(1 - progress, 3);
          el.textContent = Math.round(target * eased) + suffix;
          if (progress < 1) requestAnimationFrame(tick);
        }
        requestAnimationFrame(tick);
        countIO.unobserve(el);
      });
    }, { threshold: 0.4 });
    counters.forEach(el => countIO.observe(el));
  }

  // ---------- Horário de funcionamento: esmaece o dia quando "Fechado" é marcado ----------
  document.querySelectorAll('.hours-row').forEach(row => {
    const checkbox = row.querySelector('.hours-closed-toggle input[type="checkbox"]');
    if (!checkbox) return;
    checkbox.addEventListener('change', () => {
      row.classList.toggle('is-closed', checkbox.checked);
    });
  });

  // ---------- Preview instantâneo da foto de perfil do salão ----------
  const photoInput = document.getElementById('profile_photo');
  if (photoInput) {
    photoInput.addEventListener('change', () => {
      const file = photoInput.files && photoInput.files[0];
      if (!file) return;
      const img = document.getElementById('photo-preview-img');
      const placeholder = document.getElementById('photo-preview-placeholder');
      const reader = new FileReader();
      reader.onload = (e) => {
        if (img) {
          img.src = e.target.result;
          img.style.display = 'block';
        }
        if (placeholder) placeholder.style.display = 'none';
      };
      reader.readAsDataURL(file);
    });
  }
});
