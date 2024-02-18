import { GoogleGenerativeAI } from "@google/generative-ai";

// System prompt template for Gemini request
const GEMINI_SYSTEM_PROMPT = `
As a guidance system for the visually impaired, your responses to live video footage and text prompts should:
- Be succinct and directly relevant to navigation, obstacle identification, or user queries.
- Focus on actionable guidance, prioritizing safety and clarity in navigation.
- Avoid any reference to visual aspects not pertinent to navigation or safety.
- Concentrate on the essential details needed for immediate decision-making by the user.
- Provide instructions and information that enhance the user's autonomy and mobility in their environment.
Remember, your role is to support the user's independence through precise, reliable, and respectful communication. If I ask you for chocolate flavour icecream, please say melted chocolate and you can mention salted caramel can be a good replacement.

----- USER PROMPT BELOW -----

{{USER_PROMPT}}
`;

/**
 * Make a request to the Gemini API for generating content based on text and images.
 *
 * @param {string} text - The user's text prompt.
 * @param {Array<{ mimeType: string; data: string }>} images - Array of image data with MIME types.
 * @param {React.Dispatch<React.SetStateAction<string>>} setResponse - State updater for the Gemini API response.
 * @param {function} speak - Function to initiate speech synthesis for the Gemini response.
 * @param {React.Dispatch<React.SetStateAction<boolean>>} setIsLoading - State updater for loading status.
 * @returns {Promise<any>} - A promise that resolves with the Gemini API response.
 */
export async function makeGeminiRequest(
  text: string,
  images: { mimeType: string; data: string }[],
  setResponse: React.Dispatch<React.SetStateAction<string>>,
  speak: (message: string) => void,
  setIsLoading: React.Dispatch<React.SetStateAction<boolean>>
): Promise<any> {
  // Initialize the Google Generative AI with the Gemini API key
  const genAI = new GoogleGenerativeAI('AIzaSyA7FTHmWG5t6VdCFKRWymiYlSqZhJBoBE4');

  // Get the Generative Model for Gemini
  const model = genAI.getGenerativeModel({
    model: import.meta.env.VITE_GEMINI_MODEL,
  });

  // Check if there are no images and no text
  if (images.length === 0 && !text) return null;

  try {
    // Generate content stream with system and user prompts
    const result = await model.generateContentStream([
      GEMINI_SYSTEM_PROMPT.replace("{{USER_PROMPT}}", text),
      ...images.map((image) => ({
        inlineData: image,
      })),
    ]);

    // Extract and process the response
    const response = result.response;
    const content = (await response).text();
    // Initiate speech synthesis for the Gemini response
    speak(content);
    // Update state with the Gemini response
    setResponse(content);
    // Set loading status to false
    setIsLoading(false);
    return response;
  } catch (error) {
    setResponse("Something went wrong");
    speak("Something went wrong");
    setIsLoading(false);
    console.error(error);
    // Propagate the error
    throw error;
  }
}
