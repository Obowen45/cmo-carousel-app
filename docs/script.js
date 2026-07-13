// Scroll-linked zoom: as the user scrolls through .hero-scroll's extra
// height, the pinned logo scales up until it fills the screen with the
// bear's black fur, then a black veil fades in to hand off cleanly to the
// next (black) section.
const heroScroll = document.querySelector(".hero-scroll");
const logo = document.getElementById("logo");
const heroTitle = document.getElementById("hero-title");
const heroTagline = document.getElementById("hero-tagline");
const scrollCue = document.getElementById("scroll-cue");
const blackVeil = document.getElementById("black-veil");

const MAX_SCALE = 22;

function updateHeroZoom() {
  const scrollableHeight = heroScroll.offsetHeight - window.innerHeight;
  const rawProgress = -heroScroll.getBoundingClientRect().top / scrollableHeight;
  const progress = Math.min(Math.max(rawProgress, 0), 1);

  logo.style.transform = `scale(${1 + progress * MAX_SCALE})`;
  heroTitle.style.opacity = String(Math.max(0, 1 - progress * 4));
  heroTagline.style.opacity = String(Math.max(0, 1 - progress * 5));
  scrollCue.style.opacity = String(Math.max(0, 0.6 - progress * 6));

  const veilStart = 0.55;
  const veilProgress = Math.max(0, (progress - veilStart) / (1 - veilStart));
  blackVeil.style.opacity = String(veilProgress);
}

let ticking = false;
function onScroll() {
  if (!ticking) {
    requestAnimationFrame(() => {
      updateHeroZoom();
      ticking = false;
    });
    ticking = true;
  }
}

window.addEventListener("scroll", onScroll, { passive: true });
updateHeroZoom();

// Simple fade-in for whatever comes after the pinned hero.
const observer = new IntersectionObserver(
  (entries) => {
    for (const entry of entries) {
      if (entry.isIntersecting) {
        entry.target.classList.add("visible");
      }
    }
  },
  { threshold: 0.3 }
);

document.querySelectorAll(".reveal").forEach((el) => observer.observe(el));
