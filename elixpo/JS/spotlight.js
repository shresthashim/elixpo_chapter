

spotlightNews = [
    {
        "title": "Elixpo Art ",
        "date": "2025-07-06",
        "description": "Lorem ipsum, dolor sit amet consectetur adipisicing elit. Illum quod velit aspernatur, praesentium illo molestiae recusandae doloremque non at, corporis accusamus magni.",
        "image": "https://assets.devfolio.co/hackathons/ee8d75f60f0a4acf85238eabdea1bad3/projects/1e1a3ed29b604714b3c85d14a16e6e2d/7417c82d-02e8-4110-9dcb-91f0aaeccd91.png"
    },
    {
        "title": "Elixpo Hackathon",
        "date": "2025-07-06",
        "description": "Lorem ipsum, dolor sit amet consectetur adipisicing elit. Illum quod velit aspernatur, praesentium illo molestiae recusandae doloremque non at, corporis accusamus magni laborum earum voluptatem perferendis id quia iste saepe.",
        "image" : "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQxQODlQzQbNgLm2nwDJhfW92kSWuohZF7CvQBJaG4mC2CyZax9gexKa2wAU7jJOP5-SQk&usqp=CAU"
    },
    {
        "title": "Elixpo Tech Talks",
        "date": "2025-08-12",
        "description": "Lorem ipsum, dolor sit amet consectetur adipisicing elit. Illum quod velit aspernatur, praesentium illo molestiae recusandae doloremque non at, corporis accusamus magni laborum earum voluptatem perferendis id quia iste saepe.",
        "image": "https://images.unsplash.com/photo-1519389950473-47ba0277781c"
    },
    {
        "title": "Elixpo Community Meetup",
        "date": "2025-09-01",
        "description": "Lorem ipsum, dolor sit amet consectetur adipisicing elit. Illum quod velit aspernatur, praesentium illo molestiae recusandae doloremque non at, corporis accusamus magni laborum earum voluptatem perferendis id quia iste saepe.",
        "image": "https://images.unsplash.com/photo-1506744038136-46273834b3fb"
    },
    {
        "title": "Elixpo Coding Bootcamp",
        "date": "2025-10-15",
        "description": "Lorem ipsum, dolor sit amet consectetur adipisicing elit. Illum quod velit aspernatur, praesentium illo molestiae recusandae doloremque non at, corporis accusamus magni laborum earum voluptatem perferendis id quia iste saepe.",
        "image": "https://images.unsplash.com/photo-1461749280684-dccba630e2f6"
    }
]


function appendNews(spotlightNews) 
{
    spotlightNews.forEach(news => {
    const spotlightNode = ` 
        <div class="featuredTile relative h-[350px] w-[450px] flex-shrink-0 flex flex-col items-center mt-[10px]">
            <div class="featuredImage h-[150px] w-[90%] bg-red-500 bg-[url(${news.image})] bg-cover bg-center border-2 border-[#555]"></div>
            <span class="featuredName relative w-full flex flex-row px-[20px] items-center justify-between box-border">
                <p class="featureName text-left text-[1.5em]"> ${news.title} </p> 
                <span class="newTag relative flex h-[30px] text-[1.8em] text-[#ffc] bg-[#B63B12] items-center justify-center px-[2px] rounded-[5px] mt-[10px]"> 
                    <p> NEW </p> 
                </span> 
            </span>
            <p class="featuredDescription relative text-[1.35em] text-left px-[20px] whitespace-normal break-words w-full text-ellipsis overflow-hidden">
              ${news.description}
            </p>
        </div>
    `    
        const spotlightContainer = document.getElementById('spotlight');
         const spotlightContainer2 = document.getElementById('spotlight2')
            if (spotlightContainer && spotlightContainer2) {
                spotlightContainer.innerHTML += spotlightNode;
                spotlightContainer2.innerHTML += spotlightNode;
            }
    })
}

window.onload = function() {
    appendNews(spotlightNews);
    const appContainer = document.getElementById('appContainer');
    const punchlineSection = document.getElementById('scrollZone');
    if (appContainer && punchlineSection) {
        const appRect = appContainer.getBoundingClientRect();
        const punchlineRect = punchlineSection.getBoundingClientRect();
        const top = punchlineRect.top - appRect.top + appContainer.scrollTop;
        appContainer.scrollTo({ top, behavior: 'smooth' });
    }
    // const appContainer = document.getElementById('appContainer');
    // if (appContainer) {
    //     appContainer.scrollTop = appContainer.scrollHeight;
    // }
}
