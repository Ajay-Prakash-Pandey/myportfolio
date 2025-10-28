document.addEventListener("DOMContentLoaded", () => {
  const bars = document.querySelectorAll('.progress');
  bars.forEach(bar => {
    const width = bar.style.width;
    bar.style.width = '0%';
    setTimeout(() => {
      bar.style.width = width;
    }, 300);
  });
});