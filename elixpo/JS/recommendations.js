let recommendations = [
    {
    "content" : "Welcome to the latest catches -- in my career and let's find the craziest!!",
    "name" : "Latest Catches",
    "designation" : "Spotlight",
    "image": "../CSS/ASSESTS/spotlight/elixpo-hackathon.png"
    }
    ,
    {
        "content": "This platform helped me connect with amazing people and opportunities.",
        "name": "Alex Johnson",
        "designation": "Community Member",
        "image": "../CSS/ASSESTS/spotlight/elixpo-hackathon.png"
    },
    {
        "content": "A fantastic resource for learning and sharing new ideas.",
        "name": "Priya Singh",
        "designation": "Contributor",
        "image": "../CSS/ASSESTS/spotlight/elixpo-hackathon.png"
    },
    {
        "content": "The recommendations here are always spot on and super helpful.",
        "name": "Liam Chen",
        "designation": "Frequent Visitor",
        "image": "../CSS/ASSESTS/spotlight/elixpo-hackathon.png"
    }
]


function appendRecommendation(recommendations)
{
    const recommendationContainer = document.getElementById('recommendationSection');

    recommendations.forEach(recommendation => {
        let recommendationTile = `
        <div id="scrollZone" class="recommendationCard shrink-0 relative h-[400px] w-[650px] border-4 border-[#222] rounded-[25px] bg-[#E2D9C8] p-5 justify-center items-center mr-5 cursor-pointer hover:brightness-[85%] transition-all duration-300 ease-in-out">
          <div class="dottedContainer relative h-full w-full border-2 border-dashed border-[#222] rounded-[30px] flex flex-col gap-5 p-10 justify-between">
            <p class="quote text-[#333] text-[1.55em] whitespace-normal break-words underline decoration-1 decoration-[0.05rem] decoration-[#888] underline-offset-[6px]"> "${recommendation.content}"</p>
            <div class="attribution flex flex-row items-left gap-5">
              <div class="userLogo relative bg-[url(${recommendation.image})] bg-cover bg-center h-[65px] w-[65px] border-2 border-[#222] rounded-[50%] grayscale sepia-[50%]"></div>
              <div class="userInfo flex flex-col gap-1 leading-[30px]">
                <div class="userName font-extrabold text-[2.5em] relative tracking-wide"> ${recommendation.name} </div>
                <div class="userDesig font-thin text-[2em] relative"> ${recommendation.designation} </div>
              </div>
            </div>
            <div class="stamp absolute bottom-[20px] right-[20px] h-[80px] w-[80px] bg-[url(../CSS/ASSESTS/projects/stamp-2.png)] bg-cover bg-center "></div>
          </div> 
        </div>
    `;
        recommendationContainer.innerHTML += recommendationTile;
    });
    

    
}

appendRecommendation(recommendations);