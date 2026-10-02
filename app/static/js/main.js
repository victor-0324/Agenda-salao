// SalonPro — UI global: navegação, painel responsivo, formulários e microinterações.
document.addEventListener('DOMContentLoaded', () => {
  const body = document.body;

  // Navegação pública mobile
  const publicToggle = document.querySelector('.site-body .nav-toggle');
  const navLinks = document.querySelector('.nav-links');
  const closePublicMenu = () => {
    if (!publicToggle || !navLinks) return;
    navLinks.classList.remove('open');
    publicToggle.classList.remove('open');
    publicToggle.setAttribute('aria-expanded', 'false');
    body.style.overflow = '';
  };
  if (publicToggle && navLinks) {
    publicToggle.addEventListener('click', () => {
      const open = navLinks.classList.toggle('open');
      publicToggle.classList.toggle('open', open);
      publicToggle.setAttribute('aria-expanded', String(open));
      body.style.overflow = open ? 'hidden' : '';
    });
    navLinks.querySelectorAll('a').forEach(link => link.addEventListener('click', closePublicMenu));
  }

  // Sidebar do painel
  const sidebar = document.querySelector('.dash-sidebar');
  const sidebarToggle = document.querySelector('.sidebar-toggle');
  const overlay = document.querySelector('.sidebar-overlay');
  const closeSidebar = () => {
    sidebar?.classList.remove('open');
    overlay?.classList.remove('open');
    sidebarToggle?.setAttribute('aria-expanded', 'false');
    body.style.overflow = '';
  };
  if (sidebar && sidebarToggle) {
    sidebarToggle.setAttribute('aria-expanded', 'false');
    sidebarToggle.addEventListener('click', () => {
      const open = !sidebar.classList.contains('open');
      sidebar.classList.toggle('open', open);
      overlay?.classList.toggle('open', open);
      sidebarToggle.setAttribute('aria-expanded', String(open));
      body.style.overflow = open ? 'hidden' : '';
    });
    sidebar.querySelectorAll('a').forEach(link => link.addEventListener('click', () => {
      if (window.innerWidth <= 900) closeSidebar();
    }));
  }
  overlay?.addEventListener('click', closeSidebar);

  // Fecha menus com Escape e ao retornar ao desktop.
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      closeSidebar();
      closePublicMenu();
    }
  });
  window.addEventListener('resize', () => {
    if (window.innerWidth > 900) closeSidebar();
    if (window.innerWidth > 720) closePublicMenu();
  });

  // Reveal progressivo nas páginas públicas.
  const revealEls = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('in-view');
        observer.unobserve(entry.target);
      });
    }, { threshold: .12, rootMargin: '0px 0px -30px 0px' });
    revealEls.forEach(el => observer.observe(el));
  } else {
    revealEls.forEach(el => el.classList.add('in-view'));
  }

  // Contadores animados.
  const counters = document.querySelectorAll('[data-count]');
  if ('IntersectionObserver' in window && counters.length) {
    const countObserver = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        const el = entry.target;
        const raw = el.dataset.count || '';
        const match = raw.match(/^(\d+)(.*)$/);
        if (!match) return;
        const target = Number(match[1]);
        const suffix = match[2] || '';
        const start = performance.now();
        const duration = 800;
        const run = now => {
          const p = Math.min((now - start) / duration, 1);
          el.textContent = Math.round(target * (1 - Math.pow(1 - p, 3))) + suffix;
          if (p < 1) requestAnimationFrame(run);
        };
        requestAnimationFrame(run);
        countObserver.unobserve(el);
      });
    }, { threshold: .35 });
    counters.forEach(el => countObserver.observe(el));
  }

  // Dias fechados na configuração e agenda de profissionais.
  document.querySelectorAll('.hours-row').forEach(row => {
    const checkbox = row.querySelector('input[type="checkbox"]');
    if (!checkbox) return;
    const sync = () => row.classList.toggle('is-closed', checkbox.checked);
    checkbox.addEventListener('change', sync);
    sync();
  });

  // Preview da foto do estabelecimento.
  const photoInput = document.getElementById('profile_photo');
  photoInput?.addEventListener('change', () => {
    const file = photoInput.files?.[0];
    if (!file) return;
    const img = document.getElementById('photo-preview-img');
    const placeholder = document.getElementById('photo-preview-placeholder');
    if (!img) return;
    const reader = new FileReader();
    reader.onload = e => {
      img.src = e.target.result;
      img.classList.remove('u-hidden');
      img.style.display = 'block';
      if (placeholder) placeholder.style.display = 'none';
    };
    reader.readAsDataURL(file);
  });

  // Copiar link com feedback visual.
  document.querySelectorAll('[data-copy-target]').forEach(btn => {
    const target = document.getElementById(btn.dataset.copyTarget);
    if (!target) return;
    btn.addEventListener('click', async () => {
      const text = (btn.dataset.copyPrefix || '') + target.textContent.trim();
      try {
        await navigator.clipboard.writeText(text);
      } catch (_) {
        const area = document.createElement('textarea');
        area.value = text;
        area.style.position = 'fixed';
        area.style.opacity = '0';
        document.body.appendChild(area);
        area.select();
        document.execCommand('copy');
        area.remove();
      }
      const label = btn.querySelector('.copy-link-label');
      const original = label?.textContent || '';
      if (label) label.textContent = 'Link copiado ✓';
      btn.classList.add('is-success');
      setTimeout(() => {
        if (label) label.textContent = original;
        btn.classList.remove('is-success');
      }, 1600);
    });
  });

  // Seleção de horário da página pública.
  const slotButtons = document.querySelectorAll('.slot-btn[data-time]');
  const startTime = document.getElementById('start_time');
  const contactFields = document.getElementById('contact-fields');
  slotButtons.forEach(btn => btn.addEventListener('click', () => {
    slotButtons.forEach(item => item.classList.remove('selected'));
    btn.classList.add('selected');
    if (startTime) startTime.value = btn.dataset.time || '';
    if (contactFields) {
      contactFields.classList.remove('u-hidden');
      contactFields.style.display = 'block';
      setTimeout(() => contactFields.scrollIntoView({ behavior: 'smooth', block: 'nearest' }), 60);
    }
  }));

  // Máscara leve de telefone sem dependências externas.
  document.querySelectorAll('input[type="tel"]').forEach(input => {
    input.addEventListener('input', () => {
      const digits = input.value.replace(/\D/g, '').slice(0, 11);
      if (!digits) return;
      let value = digits;
      if (digits.length > 2) value = `(${digits.slice(0,2)}) ${digits.slice(2)}`;
      if (digits.length > 7) value = `(${digits.slice(0,2)}) ${digits.slice(2,7)}-${digits.slice(7)}`;
      input.value = value;
    });
  });

  // Auto-oculta feedbacks depois de alguns segundos, sem interromper leitura imediata.
  document.querySelectorAll('.alert').forEach(alert => {
    setTimeout(() => {
      alert.style.transition = 'opacity .25s ease, transform .25s ease';
      alert.style.opacity = '0';
      alert.style.transform = 'translateY(-4px)';
      setTimeout(() => alert.remove(), 260);
    }, 5200);
  });
});
