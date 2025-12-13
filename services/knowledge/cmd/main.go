package main

import (
	"log"
	"os"

	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/cors"
	"github.com/joho/godotenv"
)

func main() {
	godotenv.Load()

	app := fiber.New()
	app.Use(cors.New())

	app.Get("/health", func(c *fiber.Ctx) error {
		return c.JSON(fiber.Map{"status": "ok"})
	})

	// Document endpoints
	app.Post("/documents", createDocument)
	app.Get("/documents/:id", getDocument)
	app.Delete("/documents/:id", deleteDocument)

	// Search endpoints
	app.Post("/search", searchDocuments)

	port := os.Getenv("PORT")
	if port == "" {
		port = "8003"
	}

	log.Printf("Knowledge service starting on port %s", port)
	log.Fatal(app.Listen(":" + port))
}

func createDocument(c *fiber.Ctx) error {
	// TODO: Implement document creation with embeddings
	return c.Status(501).JSON(fiber.Map{"error": "Not implemented"})
}

func getDocument(c *fiber.Ctx) error {
	// TODO: Get document by ID
	return c.Status(501).JSON(fiber.Map{"error": "Not implemented"})
}

func deleteDocument(c *fiber.Ctx) error {
	// TODO: Delete document
	return c.Status(501).JSON(fiber.Map{"error": "Not implemented"})
}

func searchDocuments(c *fiber.Ctx) error {
	// TODO: Semantic search across documents
	return c.Status(501).JSON(fiber.Map{"error": "Not implemented"})
}
