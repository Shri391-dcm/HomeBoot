// ===============================
// Smooth Scroll for Navigation
// ===============================

document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener("click", function(e) {
        e.preventDefault();

        const target = document.querySelector(this.getAttribute("href"));

        if(target){
            target.scrollIntoView({
                behavior: "smooth"
            });
        }
    });
});


// ===============================
// Fade-in Animation on Scroll
// ===============================

const observer = new IntersectionObserver((entries) => {

    entries.forEach(entry => {

        if(entry.isIntersecting){

            entry.target.classList.add("show");

        }

    });

},{
    threshold:0.15
});

document.querySelectorAll("section,.card,.question-box,.brand-box").forEach(el=>{

    el.classList.add("hidden");

    observer.observe(el);

});


// ===============================
// Example Questions
// ===============================

document.querySelectorAll(".question-box").forEach(box=>{

    box.style.cursor="pointer";

    box.addEventListener("click",()=>{

        window.open(
            "http://localhost:8501",
            "_blank"
        );

    });

});


// ===============================
// Button Hover Animation
// ===============================

document.querySelectorAll(".primary,.secondary").forEach(btn=>{

    btn.addEventListener("mouseenter",()=>{

        btn.style.transform="translateY(-4px) scale(1.03)";

    });

    btn.addEventListener("mouseleave",()=>{

        btn.style.transform="translateY(0) scale(1)";

    });

});


// ===============================
// Navbar Shadow on Scroll
// ===============================

window.addEventListener("scroll",()=>{

    const nav=document.querySelector("nav");

    if(window.scrollY>20){

        nav.style.boxShadow="0 15px 35px rgba(0,0,0,.15)";

    }

    else{

        nav.style.boxShadow="0 8px 25px rgba(0,0,0,.08)";

    }

});