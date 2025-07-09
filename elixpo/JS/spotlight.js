

let spotlightNews = [
    {
        "title": "Elixpo Art ",
        "date": "2025-07-06",
        "description": "Lorem ipsum, dolor sit amet consectetur adipisicing elit. Illum quod velit aspernatur, praesentium illo molestiae recusandae doloremque non at, corporis accusamus magni.",
        "image": "../CSS/ASSESTS/spotlight/elixpo-art.png"
    },
    {
        "title": "Elixpo Hackathon",
        "date": "2025-02-06",
        "description": "Lorem ipsum, dolor sit amet consectetur adipisicing elit. Illum quod velit aspernatur, praesentium illo molestiae recusandae doloremque non at, corporis accusamus magni laborum earum voluptatem perferendis id quia iste saepe.",
        "image": "../CSS/ASSESTS/spotlight/elixpo-hackathon.png"
    },
]




function appendNews(spotlightNews) {
    const spotlightContainer = document.getElementById('spotlight');
    if (!spotlightContainer) return;
  
    let html = '';
    const now = new Date();
    const midIndex = Math.floor(spotlightNews.length / 2);
  
    spotlightNews.forEach((news, index) => {
      const newsDate = new Date(news.date);
      const diffDays = Math.abs(now - newsDate) / (1000 * 60 * 60 * 24);
      const isNew = diffDays <= 7;
  
      const newsTile = `
        <div class="featuredTile relative h-[350px] w-[400px] flex-shrink-0 flex flex-col items-center mt-[10px]">
          <div class="featuredImage hoverScale h-[150px] w-[90%] bg-[url(${news.image})] bg-cover bg-center rounded-[12px]"></div>
          <span class="featuredName relative w-full flex flex-row px-[20px] items-center justify-between box-border">
            <p class="featureName text-left text-[1.5em]"> ${news.title} </p> 
            ${isNew ? `
              <span class="newTag relative flex h-[30px] text-[1.8em] text-[#ffc] bg-[#B63B12] items-center justify-center px-[2px] rounded-[5px] mt-[10px]"> 
                <p> NEW </p> 
              </span>` : ''}
          </span>
          <p class="featuredDescription relative text-[1.35em] text-left px-[20px] whitespace-normal break-words w-full text-ellipsis overflow-hidden">
            ${news.description.slice(0, 150)}...
          </p>
        </div>
      `;
  
      // Insert special tile in the middle
      if (index === midIndex) {
        html += `
          <div class="featuredTileSpecial relative h-[350px] w-[450px] flex-shrink-0 flex flex-col items-center mt-[10px] border-r-2 border-l-2 border-[#888] px-5">
            <p class="featuredTileSpecialText text-[4em] font-extrabold tracking-wide relative"> SPOTLIGHT!</p>
            <p class="featuredTileSpecialDesc text-[1.8em] font-thin relative text-center"> Welcome to the latest catches -- in my career and let's find the craziest!!</p>
            <p class="featuredTileSpecialTip relative text-[1.5em] font-extrabold text-center top-[70px]">  &lt&lt Watch! More to Come &gt&gt </p>
          </div>
        `;
      }
  
      html += newsTile;
    });
  
    spotlightContainer.innerHTML = html;
  }
  
window.onload = function() {
    appendNews(spotlightNews);
    // const appContainer = document.getElementById('appContainer');
    // const punchlineSection = document.getElementById('scrollZone');
    // if (appContainer && punchlineSection) {
    //     const appRect = appContainer.getBoundingClientRect();
    //     const punchlineRect = punchlineSection.getBoundingClientRect();
    //     const top = punchlineRect.top - appRect.top + appContainer.scrollTop;
    //     appContainer.scrollTo({ top, behavior: 'smooth' });
    // }
    // const appContainer = document.getElementById('appContainer');
    // if (appContainer) {
    //     appContainer.scrollTop = appContainer.scrollHeight;
    // }
    
}



