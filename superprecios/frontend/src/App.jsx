// src/App.jsx
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import ProductDetail from "./pages/ProductDetail";
import "./styles.css";

function Header() {
  return (
    <header className="app-header">
      <a href="/" className="app-header__logo">
        🛒 SuperPrecios
      </a>
      <span className="app-header__tagline">
        Jumbo · Líder · Unimarc
      </span>
    </header>
  );
}

function Footer() {
  return (
    <footer className="app-footer">
      <p>SuperPrecios — Universidad Austral de Chile · INFO288</p>
    </footer>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Header />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/producto/:id" element={<ProductDetail />} />
      </Routes>
      <Footer />
    </BrowserRouter>
  );
}
