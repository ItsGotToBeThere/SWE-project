document.addEventListener("DOMContentLoaded", function(){
    const themeToggle = document.querySelector("#theme-toggle")

    // get theme and apply on page load
    const savedTheme = document.cookie.split('; ').find(row => row.startsWith('theme='));
    const currentTheme = savedTheme ? savedTheme.split('=')[1]: 'dark';

    if (currentTheme==='dark'){
        document.body.classList.remove('light')
        document.body.classList.add('dark')
        themeToggle.checked = true;
    }
    else{
        document.body.classList.remove('dark')
        document.body.classList.add('light')
        themeToggle.checked = false;
    }



    themeToggle.addEventListener("change", function(){
        let theme = document.body.classList.contains("dark") ? "light" : "dark";

        fetch(`/set-theme/?theme=${theme}`)
            .then(() => {
                document.body.classList.toggle('dark')
                document.body.classList.toggle('light')
            });

    });
});