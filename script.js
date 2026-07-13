(() => {
  'use strict';

  const nav = document.getElementById('nav');
  const menuToggle = document.getElementById('menuToggle');
  const menu = document.getElementById('menu');
  const menuLinks = menu.querySelectorAll('a');
  const form = document.querySelector('.contact__form');
  const scrollProgress = document.getElementById('scrollProgress');
  const backToTop = document.getElementById('backToTop');

  // Sticky nav background on scroll + scroll progress + back-to-top
  const updateOnScroll = () => {
    const scrollY = window.scrollY;
    const docHeight = document.documentElement.scrollHeight - window.innerHeight;
    const progress = docHeight > 0 ? (scrollY / docHeight) * 100 : 0;

    if (scrollY > 40) {
      nav.classList.add('site-nav--scrolled');
    } else {
      nav.classList.remove('site-nav--scrolled');
    }

    scrollProgress.style.width = progress + '%';

    if (scrollY > 500) {
      backToTop.classList.add('is-visible');
    } else {
      backToTop.classList.remove('is-visible');
    }
  };

  window.addEventListener('scroll', updateOnScroll, { passive: true });
  updateOnScroll();

  // Back to top
  backToTop.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });

  // Reduced motion preference check (used by browser mockup + parallax)
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Animated browser mockup in hero card
  const browser = document.querySelector('.browser');
  if (browser && !prefersReducedMotion) {
    setTimeout(() => browser.classList.add('is-building'), 400);
  }

  // Mouse parallax on hero blobs and floating shapes
  if (!prefersReducedMotion && window.matchMedia('(hover: hover)').matches) {
    const parallaxItems = [
      { selector: '.blob--one .blob__inner', factorX: -18, factorY: -18 },
      { selector: '.blob--two .blob__inner', factorX: 26, factorY: 18 },
      { selector: '.blob--three .blob__inner', factorX: -14, factorY: 22 },
      { selector: '.float-shape--star .float-shape__inner', factorX: 20, factorY: 16 },
      { selector: '.float-shape--zig .float-shape__inner', factorX: -16, factorY: -12 },
      { selector: '.float-shape--dot .float-shape__inner', factorX: 24, factorY: -18 }
    ];

    const elements = parallaxItems.map((item) => ({
      el: document.querySelector(item.selector),
      factorX: item.factorX,
      factorY: item.factorY
    })).filter((item) => item.el);

    let ticking = false;
    let mouseX = 0;
    let mouseY = 0;

    const updateParallax = () => {
      const cx = (mouseX / window.innerWidth - 0.5) * 2;
      const cy = (mouseY / window.innerHeight - 0.5) * 2;

      elements.forEach((item) => {
        const tx = cx * item.factorX;
        const ty = cy * item.factorY;
        item.el.style.transform = `translate3d(${tx}px, ${ty}px, 0)`;
      });

      ticking = false;
    };

    document.addEventListener('mousemove', (e) => {
      mouseX = e.clientX;
      mouseY = e.clientY;
      if (!ticking) {
        window.requestAnimationFrame(updateParallax);
        ticking = true;
      }
    }, { passive: true });
  }

  // Mobile menu toggle
  menuToggle.addEventListener('click', () => {
    const isOpen = menu.classList.toggle('menu--open');
    menuToggle.setAttribute('aria-expanded', String(isOpen));
  });

  // Close mobile menu when a link is clicked
  menuLinks.forEach((link) => {
    link.addEventListener('click', () => {
      menu.classList.remove('menu--open');
      menuToggle.setAttribute('aria-expanded', 'false');
    });
  });

  // 3D tilt effect on cards (desktop hover only)
  const prefersHover = window.matchMedia('(hover: hover)').matches;
  if (prefersHover) {
    const tiltCards = document.querySelectorAll('[data-tilt]');
    tiltCards.forEach((card) => {
      card.addEventListener('pointermove', (e) => {
        const rect = card.getBoundingClientRect();
        const x = (e.clientX - rect.left) / rect.width - 0.5;
        const y = (e.clientY - rect.top) / rect.height - 0.5;
        card.classList.add('is-tilting');
        card.style.transform = `perspective(800px) rotateY(${x * 8}deg) rotateX(${-y * 8}deg) translateY(-8px)`;
      });
      card.addEventListener('pointerleave', () => {
        card.classList.remove('is-tilting');
        card.style.transform = '';
      });
    });
  }

  // Basic form handling (placeholder — no backend configured)
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;

    // Simple validation
    const email = form.querySelector('#email').value.trim();
    const name = form.querySelector('#name').value.trim();
    if (!name || !email || !form.querySelector('#email').checkValidity()) {
      submitBtn.textContent = 'Please fill in name and email';
      submitBtn.style.background = 'var(--violet)';
      setTimeout(() => {
        submitBtn.textContent = originalText;
        submitBtn.style.background = '';
      }, 2500);
      return;
    }

    submitBtn.textContent = 'Message sent (demo)';
    submitBtn.style.background = 'var(--teal)';
    form.reset();
    setTimeout(() => {
      submitBtn.textContent = originalText;
      submitBtn.style.background = '';
    }, 3000);
  });

  // Reveal-on-scroll for sections and cards
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.1, rootMargin: '0px 0px -40px 0px' }
  );

  document.querySelectorAll('.service-card, .work-card, .testimonial, .about__visual, .about__content, .contact__form, .contact__content, .cta-banner__inner').forEach((el) => {
    el.classList.add('reveal');
    observer.observe(el);
  });
})();
