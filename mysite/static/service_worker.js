<!--
  Copyright (c) 2025 Hurairah
  All Rights Reserved. Proprietary Software.
  Legal matters handled by parent/guardian until age 18.
  Governed by Pakistan law (Rawalpindi jurisdiction).
-->

self.addEventListener("install", event => {
  event.waitUntil(
    caches.open("hurairahgpt-cache").then(cache => {
      return cache.addAll([
        "/",
        "/static/logo-192.png",
        "/static/logo-512.png"
      ]);
    })
  );
});

self.addEventListener("fetch", event => {
  event.respondWith(
    caches.match(event.request).then(response => {
      return response || fetch(event.request);
    })
  );
});
