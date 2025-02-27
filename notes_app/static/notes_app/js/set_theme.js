document.addEventListener("DOMContentLoaded", function(){
    const themeToggle = document.querySelector("#theme-toggle")
    const theme_icon = document.querySelector("#theme-icon")
    const black_circle = document.querySelector("#black-circle")

    // get theme and apply on page load
    const savedTheme = document.cookie.split('; ').find(row => row.startsWith('theme='));
    const currentTheme = savedTheme ? savedTheme.split('=')[1]: 'dark';

    if (currentTheme==='dark'){
        document.body.classList.remove('light')
        document.body.classList.add('dark')

        black_circle.style.opacity = 1;
        theme_icon.src = "static/notes_app/images/sun.png"
        theme_icon.alt = "dark theme"
    }
    else{
        document.body.classList.remove('dark')
        document.body.classList.add('light')
        document.body.classList.add('sun')


        black_circle.style.opacity = 0;
        theme_icon.src = "static/notes_app/images/sun.png"
        theme_icon.alt = "light theme"
    }



    themeToggle.addEventListener("click", function(){
        let theme = document.body.classList.contains("dark") ? "dark" : "light";

        fetch(`/set-theme/?theme=${theme}`)
            .then(() => {
                document.body.classList.toggle('dark')
                document.body.classList.toggle('light')
                document.body.classList.toggle('sun')
                black_circle.style.opacity = black_circle.style.opacity==="1"? "0" : "1";
            });

    });
});