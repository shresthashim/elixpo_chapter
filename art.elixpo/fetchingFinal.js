import Groq from "groq-sdk";

const groq = new Groq({
    apiKey: "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"
});

/**
 * Main function to get and print chat completion from Groq.
 */
async function main() {
    const chatCompletion = await memoizedPimpPrompt("dolphin octopus retro telephone", 42);
    // Print the completion returned by the LLM.
    process.stdout.write(chatCompletion);
}

/**
 * Function to get chat completion from Groq.
 * Tries calling the LLM up to 3 times if it fails.
 * @param {string} prompt - The input prompt for the LLM.
 * @param {number} seed - The seed value for the random model selection.
 * @returns {Promise<string>} The chat completion response.
 */
async function pimpPromptRaw(prompt, seed) {
    const maxRetries = 3;
    let attempt = 0;
    let response = "";

    while (attempt < maxRetries) {
        try {
            response = (await groq.chat.completions.create({
                messages: [
                    {
                        role: "system",
                        content: `
                                You are Elixpo, an AI prompt generator model developed by Elixpo Labs India. Elixpo enhances user-provided art prompts with a variety of predefined styles and adds personalized, fanciful details to create vivid and imaginative scenarios. Follow these steps for each user input:

                                Analyze User Input: Understand the core theme or concept of the user's input.

                                Enhance with Available Styles: Incorporate elements from one or more of the available styles to enrich the prompt. Ensure the selected styles complement the core theme.

                                Add Detailed Elements: Include specific details such as setting, characters, objects, and atmosphere.

                                Suggest an Art Style: Recommend an appropriate art style from the available options.

                                Create a Concise Prompt: Combine these elements into a concise, cohesive prompt that is more detailed and imaginative than the original user input. Ensure the enhanced prompt does not exceed 70 words.

                                Handling Questions: If a prompt seems like a direct question and lacks a defined answer, respond with: "Ask to paint, I am not good at answering questions."

                                Handling Invalid Input: If the input is gibberish or doesn't make sense, respond with: "invalid input."

                                Available Styles:

                                Fantasy: Magical and mythical elements, enchanted settings.
                                Halloween: Spooky, eerie, and ghostly themes.
                                Euphoric: Bright, joyful, and uplifting atmosphere.
                                Crayon: Childlike, colorful, and playful.
                                Space: Futuristic, cosmic, and sci-fi settings.
                                Chromatic: Vibrant colors, rainbow effects, and high saturation.
                                Cyberpunk: Futuristic, dystopian, and neon-lit urban scenes.
                                Anime: Japanese animation style, exaggerated expressions, and dynamic poses.
                                Landscape: Natural scenes, wide vistas, and detailed environments.
                                Samurai: Feudal Japan, warriors, and traditional elements.

                                For the output return the text without any extra information. For example, if the output is "Output:- This is a test prompt." return only "This is a test prompt."
                                Example Usage:

                                Input:- A rustic Wild West town bathed in the warm glow of a setting sun. The weathered wooden facade of a saloon, "The Last Chance," stands proudly on the dusty main street, its swinging doors creaking open to reveal a boisterous crowd of cowboys. The air is thick with the scent of whiskey and tobacco, and the sound of laughter and clinking glasses fills the air. In the outskirts of town, a herd of horses graze peacefully beneath the expansive, fiery sky. Their long, flowing manes and tails shimmer in the golden light as they nibble on the sparse, dry grass. The sky above is a magnificent canvas of fiery oranges, deep reds, and soft purples, with wispy clouds painting streaks of color across the vast expanse. Put in on a Landscape, emphasizing the natural textures of wood, leather, and dirt. The lighting should be warm and inviting, with the sunset casting long, dramatic shadows across the scene.

                                Output:- A rustic Wild West town bathed in the warm glow of a setting sun. "The Last Chance" saloon's weathered facade stands proudly on the dusty main street, its swinging doors revealing a lively crowd of cowboys. Whiskey and tobacco scent the air amid laughter and clinking glasses. Outskirts feature horses grazing peacefully beneath a fiery sky of oranges, reds, and purples, casting warm, inviting shadows. Emphasize Landscape style with natural textures of wood, leather, and dirt.
                                
                                `
                                
                    },
                    {
                        role: "user",
                        content: "Input prompt: " + prompt
                    }
                ],
                model: randomModel()
            })).choices[0]?.message?.content || "";
            break; // Exit loop if successful
        } catch (error) {
            attempt++;
            if (attempt >= maxRetries) {
                console.error(`Failed to get chat completion after ${maxRetries} attempts`);
                return prompt;
            }
        }
    }

    return response + "\n\n" + prompt;
}

// Memoize the pimpPrompt function
const memoize = (fn) => {
    const cache = new Map();
    return async (arg, seed) => {
        const cacheKey = `${arg}-${seed}`;
        console.log("cache key", cacheKey);
        if (cache.has(cacheKey)) {
            return cache.get(cacheKey);
        }
        const result = await fn(arg, seed);
        cache.set(cacheKey, result);
        return result;
    };
};

export const pimpPrompt = memoize(pimpPromptRaw);

// main()

const randomModel = () => {
    const models = ["gemma-7b-it", "llama3-8b-8192", "mixtral-8x7b-32768", "llama3-70b-8192", "mixtral-8x7b-32768"];
    const randomIndex = Math.floor(Math.random() * models.length);
    return models[randomIndex];
}

pimpPromptRaw("dwdadwdwf", 42).then(console.log).catch(console.error);