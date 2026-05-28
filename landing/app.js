const videos = Array.from(document.querySelectorAll(".autoplay-video"));

for (const video of videos) {
  video.muted = true;
  video.defaultMuted = true;
  video.loop = true;
  video.playsInline = true;
  video.setAttribute("webkit-playsinline", "");
  video.preload = "auto";
}

const tryPlay = async (video) => {
  try {
    await video.play();
  } catch (_) {
    // Mobile browsers can still block autoplay in edge cases.
  }
};

const observer = new IntersectionObserver(
  (entries) => {
    for (const entry of entries) {
      const video = entry.target;
      if (!(video instanceof HTMLVideoElement)) {
        continue;
      }

      if (entry.isIntersecting && entry.intersectionRatio >= 0.3) {
        void tryPlay(video);
      } else {
        video.pause();
      }
    }
  },
  {
    rootMargin: "140px 0px 140px 0px",
    threshold: [0, 0.12, 0.3, 0.6, 0.85],
  }
);

for (const video of videos) {
  observer.observe(video);
  void tryPlay(video);
}

document.addEventListener("visibilitychange", () => {
  for (const video of videos) {
    if (document.hidden) {
      video.pause();
    } else {
      void tryPlay(video);
    }
  }
});
