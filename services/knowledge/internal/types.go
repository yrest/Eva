package internal

type Document struct {
	ID        string            `json:"id"`
	Title     string            `json:"title"`
	Content   string            `json:"content"`
	Embedding []float32         `json:"embedding,omitempty"`
	Metadata  map[string]string `json:"metadata,omitempty"`
	CreatedAt string            `json:"created_at"`
	UpdatedAt string            `json:"updated_at"`
}

type SearchRequest struct {
	Query  string `json:"query"`
	Limit  int    `json:"limit"`
	Filter map[string]string `json:"filter,omitempty"`
}

type SearchResult struct {
	Document Document `json:"document"`
	Score    float32  `json:"score"`
}
