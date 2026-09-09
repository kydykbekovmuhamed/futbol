// Service worker для фоновых push-уведомлений (вкладка закрыта/неактивна).
// Отдельный контекст от app.js — свой initializeApp с тем же публичным
// конфигом (firebaseConfig не секретный, безопасно встраивать в клиентский
// код, в отличие от serverside service-account JSON в secrets/).
importScripts("https://www.gstatic.com/firebasejs/10.14.1/firebase-app-compat.js");
importScripts("https://www.gstatic.com/firebasejs/10.14.1/firebase-messaging-compat.js");

firebase.initializeApp({
  apiKey: "AIzaSyAJR17Q-JBedIbtY533ElecSM7MDvy1Og0",
  authDomain: "futbol-app-4f955.firebaseapp.com",
  projectId: "futbol-app-4f955",
  storageBucket: "futbol-app-4f955.firebasestorage.app",
  messagingSenderId: "863563525836",
  appId: "1:863563525836:web:2b98399d3d55f622b3dc69"
});

var messaging = firebase.messaging();

messaging.onBackgroundMessage(function (payload) {
  var title = (payload.notification && payload.notification.title) || "Футбол";
  var body = (payload.notification && payload.notification.body) || "";
  self.registration.showNotification(title, { body: body });
});
