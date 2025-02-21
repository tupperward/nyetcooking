package main

import (
		"fmt"
		"io"
		"net/http"
		"os"
		"path/filepath"
		"strings"
		"encoding/json"
		_ "embed"
		"flag"

		"github.com/nikolalohinski/gonja/v2"
		"github.com/nikolalohinski/gonja/v2/exec"
)

type Recipe struct{
	Title string `json:"name"`
	Description string `json:"description"`
	RecipeIngredient string `json:"recipeIngredient"`
	RecipeInstructions string `json:"recipeInstructions"`
	Image Image `json:"image"`
}

type Image struct {
	Url string `json:"url"`
}

func findFirstLDJSONBlock(html string) (string, error) {
	start := strings.Index(html, `<script type="application/ld+json">`)
	if start == -1 {
			return "", fmt.Errorf("no LD+JSON block found")
	}

	end := strings.Index(html[start:], "</script>")
	if end == -1 {
			return "", fmt.Errorf("malformed LD+JSON block")
	}

// Calculate the absolute end position in the original string
	end += start
	ldjson := html[start+len(`<script type="application/ld+json">`):end]
	return ldjson, nil
}

func extractLDJSON(url string) (string, error) {
	resp, err := http.Get(url)
	if err != nil {
			return "", err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
			return "", err
	}
	searchableBody := string(body)

	// Find LD+JSON blocks
	ldjsonBlocks, err:= findFirstLDJSONBlock(searchableBody)
	if err != nil {
		return "", fmt.Errorf("error finding LD+JSON: %w", err) // Wrap the original error
	}

	s := []string{ldjsonBlocks}
	return strings.Join(s, "\n"), nil
}

//go:embed go_recipe_card.html
var recipeTemplate string 

func createBasicWebpage(ldjson string, noImage bool) (string, error) {
	// Parse JSON into a generic map
	var data map[string]interface{}
	err := json.Unmarshal([]byte(ldjson), &data)
	if err != nil {
		return "", err
	}

	// Parse the embedded template
	tpl, err := gonja.FromString(recipeTemplate)
	if err != nil {
		return "", fmt.Errorf("error parsing template: %w", err)
	}

	// Create the context for the Gonja template
	
	// Create Gonja execution context
	ctx := exec.NewContext(map[string]interface{}{
		"recipe": data,
		"no_image": noImage, // Pass the noImage flag
	})

	// Render template to string
	rendered, err := tpl.ExecuteToString(ctx)
	if err != nil {
		return "", fmt.Errorf("error rendering template: %w", err)
	}

	return rendered, nil
}

func main() {
	// Set up flags
	var outputDir string 
	flag.StringVar(&outputDir, "o", "", "Output to a specific file path")

	var url string
	flag.StringVar(&url, "url", "", "NYT Cooking URL to retrieve")

	var noImage bool
	flag.BoolVar(&noImage, "no-image", false, "Do not render the included image (saves printer ink)")
	
	flag.Parse()

	// Get URL from argument if the flag isn't set
	if url == "" {
		url = os.Args[1]
	}

	// Get the output directory from argument if the flag isn't set
	if outputDir == "" {
		if len(os.Args) == 3 {
			outputDir = os.Args[2]
		}
	}
	
	// Fetch LD+JSON data
	ldjson, err := extractLDJSON(url)
	if err != nil {
		fmt.Println("Error:", err)
		return
	}

	// Generate HTML from the template
	html, err := createBasicWebpage(ldjson, noImage)
	if err != nil {
		fmt.Println("Error creating webpage:", err)
		return
	}
	
	// Build output file path
	if outputDir == "" {
		outputDir = "./"
	}

	filename := filepath.Base(url) + ".html"
	filePath := filepath.Join(outputDir, filename)

	// Write HTML content to file
	err = os.WriteFile(filePath, []byte(html), 0644)
	if err != nil {
		fmt.Println("Error writing HTML file:", err)
		return
	}

	fmt.Println("Recipe page saved to", filePath)
}