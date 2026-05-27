const videos = Array.from(document.querySelectorAll(".autoplay-video"));

for (const video of videos) {
  video.muted = true;
  video.defaultMuted = true;
  video.loop = true;
  video.playsInline = true;
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

      if (entry.isIntersecting && entry.intersectionRatio >= 0.55) {
        void tryPlay(video);
      } else {
        video.pause();
      }
    }
  },
  {
    threshold: [0, 0.25, 0.55, 0.8],
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
