class ThemeLibraryPanel extends HTMLElement {
  set hass(hass) {
    this._hass = hass;
    if (!this._iframe) {
      const token = hass && hass.auth && hass.auth.data ? hass.auth.data.access_token : "";
      this._iframe = document.createElement("iframe");
      this._iframe.src = `/theme_library_static/index.html?token=${encodeURIComponent(token)}`;
      this._iframe.style.cssText = "width:100%;height:100%;border:none;display:block;";
      this.appendChild(this._iframe);
    }
  }

  connectedCallback() {
    this.style.cssText = "display:block;width:100%;height:100%;";
  }
}

customElements.define("theme-library-panel", ThemeLibraryPanel);
