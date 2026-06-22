import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

const firebaseConfig = {
  apiKey: "AIzaSyDjKC8WF3c_yYHplg2GG7oP0hrI15QyKuE",
  authDomain: "compact-iq-1533e.firebaseapp.com",
  projectId: "compact-iq-1533e",
  storageBucket: "compact-iq-1533e.firebasestorage.app",
  messagingSenderId: "1029187936963",
  appId: "1:1029187936963:web:1fe99037d78e398430b876",
};

const app = initializeApp(firebaseConfig);

export const auth = getAuth(app);
