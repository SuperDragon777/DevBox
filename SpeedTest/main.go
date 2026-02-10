package main

import (
	"context"
	"crypto/rand"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"
)

var downloadServers = []string{
	"https://proof.ovh.net/files/100Mb.dat",
	"https://speedtest.selectel.ru/100MB",
	"http://ipv4.download.thinkbroadband.com/100MB.zip",
}

var pingServers = []string{
	"https://www.google.com/favicon.ico",
	"https://www.cloudflare.com/favicon.ico",
	"https://www.github.com/favicon.ico",
}

const uploadURL = "https://httpbin.org/post"

type SpeedResult struct {
	Timestamp    time.Time `json:"timestamp"`
	DownloadMbps float64   `json:"download_mbps"`
	UploadMbps   float64   `json:"upload_mbps"`
	Latency      float64   `json:"latency_ms"`
	Server       string    `json:"server"`
}

type HistoryManager struct {
	Path    string
	Results []SpeedResult
}

func NewHistoryManager() *HistoryManager {
	home, _ := os.UserHomeDir()
	h := &HistoryManager{
		Path: filepath.Join(home, ".speedtest_history.json"),
	}
	h.load()
	return h
}

func (h *HistoryManager) load() {
	data, err := os.ReadFile(h.Path)
	if err == nil {
		_ = json.Unmarshal(data, &h.Results)
	}
}

func (h *HistoryManager) save() {
	if len(h.Results) > 100 {
		h.Results = h.Results[len(h.Results)-100:]
	}
	data, _ := json.MarshalIndent(h.Results, "", "  ")
	_ = os.WriteFile(h.Path, data, 0644)
}

func (h *HistoryManager) add(r SpeedResult) {
	h.Results = append(h.Results, r)
	h.save()
}

func measureLatency() float64 {
	fmt.Print("  Testing latency... ")

	client := http.Client{Timeout: 5 * time.Second}
	var sum float64
	var ok int

	for _, url := range pingServers {
		start := time.Now()
		resp, err := client.Get(url)
		if err != nil {
			continue
		}
		resp.Body.Close()
		sum += float64(time.Since(start).Milliseconds())
		ok++
	}

	if ok == 0 {
		fmt.Println("FAILED")
		return -1
	}

	avg := sum / float64(ok)
	fmt.Printf("%.2f ms\n", avg)
	return avg
}

func measureDownloadSpeed() float64 {
	fmt.Println("  Testing download speed...")

	client := http.Client{
		Transport: &http.Transport{
			DisableCompression: true,
		},
	}

	for _, url := range downloadServers {
		fmt.Printf("    → %s\n", url)

		ctx, cancel := context.WithTimeout(context.Background(), 90*time.Second)
		req, _ := http.NewRequestWithContext(ctx, "GET", url, nil)

		start := time.Now()
		resp, err := client.Do(req)
		if err != nil {
			fmt.Println("      FAILED:", err)
			cancel()
			continue
		}

		if resp.StatusCode >= 400 {
			fmt.Println("      FAILED:", resp.Status)
			resp.Body.Close()
			cancel()
			continue
		}

		n, err := io.Copy(io.Discard, resp.Body)
		resp.Body.Close()
		cancel()

		if err != nil {
			fmt.Println("      FAILED:", err)
			continue
		}

		elapsed := time.Since(start).Seconds()
		mbps := float64(n*8) / (elapsed * 1e6)

		fmt.Printf("      OK: %.2f Mbps (%s in %.1fs)\n",
			mbps, formatSize(n), elapsed)

		return mbps
	}

	fmt.Println("  ❌ All download servers failed")
	return -1
}

type randomReader struct{}

func (r randomReader) Read(p []byte) (int, error) {
	return rand.Read(p)
}

func measureUploadSpeed() float64 {
	fmt.Print("  Testing upload speed... ")

	const size = int64(50 * 1024 * 1024)

	reader := io.LimitReader(randomReader{}, size)
	req, _ := http.NewRequest("POST", uploadURL, reader)
	req.ContentLength = size
	req.Header.Set("Content-Type", "application/octet-stream")

	client := http.Client{Timeout: 90 * time.Second}
	start := time.Now()

	resp, err := client.Do(req)
	if err != nil {
		fmt.Println("FAILED:", err)
		return -1
	}
	defer resp.Body.Close()

	io.Copy(io.Discard, resp.Body)

	elapsed := time.Since(start).Seconds()
	mbps := float64(size*8) / (elapsed * 1e6)

	fmt.Printf("%.2f Mbps (%s in %.1fs)\n", mbps, formatSize(size), elapsed)
	return mbps
}

func formatSize(b int64) string {
	const unit = 1024
	if b < unit {
		return fmt.Sprintf("%d B", b)
	}
	div, exp := int64(unit), 0
	for n := b / unit; n >= unit; n /= unit {
		div *= unit
		exp++
	}
	return fmt.Sprintf("%.1f %cB", float64(b)/float64(div), "KMGTPE"[exp])
}

func main() {
	history := flag.Bool("history", false, "Show history")
	limit := flag.Int("limit", 10, "History limit")
	noSave := flag.Bool("no-save", false, "Don't save result")
	flag.Parse()

	hm := NewHistoryManager()

	if *history {
		start := len(hm.Results) - *limit
		if start < 0 {
			start = 0
		}
		for _, r := range hm.Results[start:] {
			fmt.Printf("[%s] ↓ %.2f ↑ %.2f ⚡ %.2f ms\n",
				r.Timestamp.Format("2006-01-02 15:04:05"),
				r.DownloadMbps,
				r.UploadMbps,
				r.Latency,
			)
		}
		return
	}

	fmt.Println("\n📡 Measuring latency...")
	latency := measureLatency()

	fmt.Println("\n⬇️  Measuring download...")
	download := measureDownloadSpeed()

	fmt.Println("\n⬆️  Measuring upload...")
	upload := measureUploadSpeed()

	fmt.Println("\n════════ RESULTS ════════")
	fmt.Printf("⬇️ Download: %.2f Mbps\n", download)
	fmt.Printf("⬆️ Upload:   %.2f Mbps\n", upload)
	fmt.Printf("⚡ Latency:  %.2f ms\n", latency)

	if !*noSave {
		hm.add(SpeedResult{
			Timestamp:    time.Now(),
			DownloadMbps: download,
			UploadMbps:   upload,
			Latency:      latency,
			Server:       strings.Join(downloadServers, ", "),
		})
		fmt.Println("✅ Saved to history")
	}
}
