(() => {
  function generateQRCode(container, url) {
    container.innerHTML = "";
    if (!window.QRCode) {
      throw new Error("QRCode library not loaded");
    }

    // eslint-disable-next-line no-new
    new window.QRCode(container, {
      text: url,
      width: 180,
      height: 180,
      colorDark: "#111111",
      colorLight: "#ffffff",
      correctLevel: window.QRCode.CorrectLevel.H,
    });
  }

  window.QRGenerator = {
    generateQRCode,
  };
})();
