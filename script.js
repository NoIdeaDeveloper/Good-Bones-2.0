// Good Bones site scripts — ES module
// No top-level IIFE needed; modules are implicitly strict and scoped.

const nav = document.getElementById('nav');
const menuToggle = document.getElementById('menuToggle');
const menu = document.getElementById('menu');
const menuLinks = menu ? menu.querySelectorAll('a') : [];
const form = document.querySelector('.contact__form');
const scrollProgress = document.getElementById('scrollProgress');
const backToTop = document.getElementById('backToTop');

// Sticky nav background on scroll + scroll progress + back-to-top
const updateOnScroll = () => {
    const scrollY = window.scrollY;
    const docHeight = document.documentElement.scrollHeight - window.innerHeight;
    const progress = docHeight > 0 ? (scrollY / docHeight) * 100 : 0;

    if (nav) {
      if (scrollY > 0) {
        nav.classList.add('site-nav--scrolled');
      } else {
        nav.classList.remove('site-nav--scrolled');
      }
    }

    if (scrollProgress) {
      scrollProgress.style.width = progress + '%';
    }

    if (backToTop) {
      if (scrollY > 500) {
        backToTop.classList.add('is-visible');
      } else {
        backToTop.classList.remove('is-visible');
      }
    }
  };

window.addEventListener('scroll', updateOnScroll, { passive: true });
updateOnScroll();

// Back to top
if (backToTop) {
  backToTop.addEventListener('click', () => {
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    window.scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' });
  });
}

// Page-type guards: heavy homepage-only effects should only initialise when
// the corresponding DOM exists. This avoids wasted CPU/memory on blog,
// legal and 404 pages that share script.js.
const hasHomepageHero = !!document.querySelector('.hero');

// Reduced motion preference check (used by browser mockup + parallax)
const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

// Animated browser mockup in hero card
if (hasHomepageHero) {
  const browser = document.querySelector('.browser');
  if (browser && !prefersReducedMotion) {
    setTimeout(() => browser.classList.add('is-building'), 400);
  }
}

// Mouse parallax on hero blobs and floating shapes
if (hasHomepageHero && !prefersReducedMotion && window.matchMedia('(hover: hover)').matches) {
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

    const siteFooter = document.querySelector('.site-footer');

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

      if (siteFooter) {
        siteFooter.style.setProperty('--footer-bg-x', `${-cx * 18}px`);
        siteFooter.style.setProperty('--footer-bg-y', `${-cy * 18}px`);
      }

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
if (menuToggle && menu) {
  const mobileMenuQuery = window.matchMedia('(max-width: 720px)');
  const isMobileMenu = () => mobileMenuQuery.matches;

  const updateMenuState = (isOpen) => {
    menu.classList.toggle('menu--open', isOpen);
    menuToggle.setAttribute('aria-expanded', String(isOpen));
    menuToggle.setAttribute('aria-label', isOpen ? 'Close menu' : 'Open menu');

    // Keep the hidden mobile menu out of the keyboard/AT order when closed.
    if (isMobileMenu()) {
      menu.inert = !isOpen;
      menu.setAttribute('aria-hidden', String(!isOpen));
    } else {
      menu.inert = false;
      menu.removeAttribute('aria-hidden');
    }
  };

  updateMenuState(false);

  menuToggle.addEventListener('click', () => {
    const willOpen = !menu.classList.contains('menu--open');
    updateMenuState(willOpen);
    if (willOpen && isMobileMenu() && menuLinks.length) {
      menuLinks[0].focus();
    }
  });

  // Close mobile menu when a link is clicked
  menuLinks.forEach((link) => {
    link.addEventListener('click', () => updateMenuState(false));
  });

  // Close on Escape or when clicking outside the open menu
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && menu.classList.contains('menu--open')) {
      updateMenuState(false);
      menuToggle.focus();
    }
  });

  document.addEventListener('click', (e) => {
    if (
      menu.classList.contains('menu--open') &&
      !menu.contains(e.target) &&
      !menuToggle.contains(e.target)
    ) {
      updateMenuState(false);
    }
  });

  // Re-apply accessibility state when crossing the mobile breakpoint
  mobileMenuQuery.addEventListener('change', () => updateMenuState(menu.classList.contains('menu--open')));
}

// 3D tilt effect on cards (desktop hover only, respects reduced-motion)
const prefersHover = window.matchMedia('(hover: hover)').matches;
if (hasHomepageHero && prefersHover && !prefersReducedMotion) {
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
const initForm = (formEl) => {
  if (!formEl) return;

  const errorIdFor = (field) => {
    const describedBy = field.getAttribute('aria-describedby');
    if (!describedBy) return null;
    // aria-describedby can hold multiple IDs; the first one points to the inline error.
    return describedBy.split(' ')[0];
  };

  const setError = (field, message) => {
    const errorEl = document.getElementById(errorIdFor(field));
    if (errorEl) {
      errorEl.textContent = message;
    }
    field.setAttribute('aria-invalid', 'true');
  };

  const clearError = (field) => {
    const errorEl = document.getElementById(errorIdFor(field));
    if (errorEl) {
      errorEl.textContent = '';
    }
    field.setAttribute('aria-invalid', 'false');
  };

  const labelFor = (field) => {
    const label = formEl.querySelector(`label[for="${field.id}"]`);
    return label ? label.textContent.trim() : field.name || 'This field';
  };

  const validateField = (field) => {
    const value = field.value.trim();
    if (field.required && !value) {
      setError(field, `${labelFor(field)} is required`);
      return false;
    }
    if (field.type === 'email' && value && !field.checkValidity()) {
      setError(field, 'Please enter a valid email address');
      return false;
    }
    clearError(field);
    return true;
  };

  const requiredFields = formEl.querySelectorAll('input[required], select[required], textarea[required]');
  requiredFields.forEach((field) => {
    field.addEventListener('blur', () => validateField(field));
    field.addEventListener('input', () => {
      if (field.getAttribute('aria-invalid') === 'true') {
        validateField(field);
      }
    });
  });

  formEl.addEventListener('submit', (event) => {
    event.preventDefault();
    const submitBtn = formEl.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    const fields = Array.from(requiredFields);

    const allValid = fields.map(validateField).every(Boolean);

    if (!allValid) {
      const firstInvalid = formEl.querySelector('[aria-invalid="true"]');
      if (firstInvalid) {
        firstInvalid.focus();
      }
      submitBtn.textContent = 'Please fix the errors above';
      submitBtn.style.background = 'var(--violet)';
      setTimeout(() => {
        submitBtn.textContent = originalText;
        submitBtn.style.background = '';
      }, 2500);
      return;
    }

    submitBtn.textContent = 'Message sent (demo)';
    submitBtn.style.background = 'var(--teal)';
    formEl.reset();
    fields.forEach(clearError);
    setTimeout(() => {
      submitBtn.textContent = originalText;
      submitBtn.style.background = '';
    }, 3000);
  });
};

initForm(form);
initForm(document.querySelector('.privacy-form'));

// Reveal-on-scroll for sections and cards (homepage only)
if (hasHomepageHero) {
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

  document.querySelectorAll('.hero__content').forEach((el) => {
    el.classList.add('reveal');
    observer.observe(el);
  });

  document.querySelectorAll('.section__header').forEach((el) => {
    el.classList.add('reveal');
    observer.observe(el);
  });

  document.querySelectorAll('.service-card, .work-card, .testimonial, .about__visual, .about__content, .contact__form, .contact__content, .cta-banner__inner, .hero__card').forEach((el, index) => {
    el.classList.add('reveal');
    el.style.setProperty('--reveal-index', index);
    observer.observe(el);
  });

  // Count-up animation for About stats
  const countObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        const stat = entry.target;
        const target = Number(stat.dataset.count);
        const strong = stat.querySelector('strong');
        const suffix = strong.textContent.replace(/[0-9]/g, '');

        if (target <= 1) {
          // Skip animation for very small numbers; it feels underwhelming.
          strong.textContent = target + suffix;
          countObserver.unobserve(stat);
          return;
        }

        const duration = 1200;
        const start = performance.now();
        const step = (now) => {
          const progress = Math.min((now - start) / duration, 1);
          const ease = 1 - Math.pow(1 - progress, 3);
          const value = Math.floor(ease * target);
          strong.textContent = value + suffix;
          if (progress < 1) {
            requestAnimationFrame(step);
          }
        };
        requestAnimationFrame(step);
        countObserver.unobserve(stat);
      });
    },
    { threshold: 0.5 }
  );

  document.querySelectorAll('.about__stat').forEach((stat) => countObserver.observe(stat));
}

// Legal table-of-contents active-state highlighting
const tocLinks = document.querySelectorAll('.legal-toc a');
const legalSections = document.querySelectorAll('.legal-content section[id]');
if (tocLinks.length && legalSections.length) {
  const navHeight = nav ? nav.offsetHeight : 90;
  const offset = navHeight + 32;

  const updateTocActive = () => {
    const scrollPos = window.scrollY + offset;
    let activeId = '';

    // Highlight the section whose content is currently at the reading position.
    for (const section of legalSections) {
      const top = section.offsetTop;
      const bottom = top + section.offsetHeight;
      if (scrollPos >= top && scrollPos < bottom) {
        activeId = section.id;
        break;
      }
    }

    // Fallback: above all sections -> first; below all sections -> last.
    if (!activeId && legalSections.length) {
      const first = legalSections[0];
      const last = legalSections[legalSections.length - 1];
      if (scrollPos < first.offsetTop) {
        activeId = first.id;
      } else if (scrollPos >= last.offsetTop + last.offsetHeight) {
        activeId = last.id;
      }
    }

    tocLinks.forEach((link) => {
      link.classList.toggle('is-active', link.getAttribute('href') === '#' + activeId);
    });
  };

  window.addEventListener('scroll', updateTocActive, { passive: true });
  updateTocActive();
}
