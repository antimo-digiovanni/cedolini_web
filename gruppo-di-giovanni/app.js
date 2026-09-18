document.getElementById('year').textContent = new Date().getFullYear();

(function () {
  var header = document.querySelector('[data-hdr]');
  if (!header) return;
  var onScroll = function () {
    if (window.scrollY > 40) header.classList.add('is-scrolled');
    else header.classList.remove('is-scrolled');
  };
  onScroll();
  window.addEventListener('scroll', onScroll, { passive: true });
})();

(function () {
  if (typeof gsap === 'undefined' || typeof ScrollTrigger === 'undefined') return;
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  document.documentElement.classList.add('gsap-ready');
  gsap.registerPlugin(ScrollTrigger);

  var mm = gsap.matchMedia();

  mm.add({ isDesktop: '(min-width: 981px)', isMobile: '(max-width: 980px)' }, function (context) {
    var isDesktop = context.conditions.isDesktop;
    var cleanup = [];

    // Establish GSAP-owned starting values.
    gsap.set('[data-line] > span', { opacity: 0, y: 26 });
    gsap.set('.node[data-node]', { opacity: 0 });
    gsap.set('.hero-bottom, .hero-caption', { opacity: 0, y: 16 });
    gsap.set('[data-fade]', { opacity: 0, y: 34 });
    gsap.set('[data-mark]', { opacity: 0, y: 18 });
    gsap.set('.story-media img.card-photo', { scale: 1.12 });

    // Hero: line reveal + fade-up content on load.
    var heroTl = gsap.timeline({ delay: 0.15, defaults: { ease: 'power3.out' } });
    heroTl
      .to('.hero [data-line] > span', { opacity: 1, y: 0, duration: 1, stagger: 0.12 })
      .to('.hero-bottom, .hero-caption', { opacity: 1, y: 0, duration: 0.9 }, '-=0.6');
    cleanup.push(heroTl);

    // Constellation: four identities converging toward the group mark.
    var paths = gsap.utils.toArray('.cline');
    paths.forEach(function (p) {
      var len = p.getTotalLength();
      p.style.strokeDasharray = len;
      p.style.strokeDashoffset = len;
    });

    if (isDesktop) {
      var lineTl = gsap.timeline({
        scrollTrigger: { trigger: '.hero', start: 'top top', end: '+=26%', scrub: 0.6 }
      });
      lineTl
        .to('.node[data-node]', { opacity: 1, duration: 1, stagger: 0.12 }, 0)
        .to(paths, { strokeDashoffset: 0, duration: 1, stagger: 0.12, ease: 'none' }, 0.05);
      cleanup.push(lineTl);

      var parallax = gsap.to('.hero-bg img', {
        yPercent: 6,
        ease: 'none',
        scrollTrigger: { trigger: '.hero', start: 'top top', end: 'bottom top', scrub: 0.6 }
      });
      cleanup.push(parallax);
    } else {
      gsap.set('.node[data-node]', { opacity: 1 });
      gsap.set(paths, { strokeDashoffset: 0 });
    }

    // Company stories: image settle + staggered copy reveal per section.
    gsap.utils.toArray('[data-story]').forEach(function (story) {
      var tl = gsap.timeline({
        scrollTrigger: { trigger: story, start: 'top 78%', toggleActions: 'play none none none' }
      });
      var photo = story.querySelector('.card-photo');
      if (photo) tl.to(photo, { scale: 1, duration: 1.3, ease: 'power2.out' }, 0);
      tl.to(story.querySelectorAll('[data-fade]'), { opacity: 1, y: 0, duration: 0.8, stagger: 0.08, ease: 'power3.out' }, 0.1);
      var mark = story.querySelector('[data-mark]');
      if (mark) tl.to(mark, { opacity: 1, y: 0, duration: 0.8 }, 0.15);
      cleanup.push(tl);
    });

    // "Il legame": emotional statement reveal.
    var bondTl = gsap.timeline({
      scrollTrigger: { trigger: '.bond', start: 'top 70%', toggleActions: 'play none none none' }
    });
    bondTl
      .to('.bond [data-line] > span', { opacity: 1, y: 0, duration: 1, stagger: 0.15, ease: 'power3.out' })
      .to('.bond [data-fade]', { opacity: 1, y: 0, duration: 0.8, stagger: 0.1, ease: 'power3.out' }, '-=0.5');
    cleanup.push(bondTl);

    return function () {
      cleanup.forEach(function (t) { t.scrollTrigger && t.scrollTrigger.kill(); t.kill(); });
    };
  });
})();
