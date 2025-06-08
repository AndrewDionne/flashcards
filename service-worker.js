
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open('polish-numbers-cache').then((cache) => {
            return cache.addAll([
                '/',
                '/index.html',
                '/manifest.json',
                '/service-worker.js',
                '/audio/1.mp3',
                '/audio/2.mp3',
                '/audio/3.mp3',
                '/audio/4.mp3',
                '/audio/5.mp3',
                '/audio/6.mp3',
                '/audio/7.mp3',
                '/audio/8.mp3',
                '/audio/9.mp3',
                '/audio/10.mp3',
                '/audio/11.mp3',
                '/audio/12.mp3',
                '/audio/13.mp3',
                '/audio/14.mp3',
                '/audio/15.mp3',
                '/audio/16.mp3',
                '/audio/17.mp3',
                '/audio/18.mp3',
                '/audio/19.mp3',
                '/audio/20.mp3'
            ]);
        })
    );
});

self.addEventListener('fetch', (event) => {
    event.respondWith(
        caches.match(event.request).then((response) => {
            return response || fetch(event.request);
        })
    );
});
