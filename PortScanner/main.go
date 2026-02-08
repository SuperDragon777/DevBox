package main

// go build -o portscan.exe ~\DevBox\PortScanner\main.go
// Usage: portscan <host> [port-range] [options]

import (
	"flag"
	"fmt"
	"net"
	"os"
	"sort"
	"sync"
	"time"
)

type ScanResult struct {
	Port   int
	Status string
}

type Scanner struct {
	Host    string
	Timeout time.Duration
	Workers int
}

func NewScanner(host string, timeout time.Duration, workers int) *Scanner {
	return &Scanner{
		Host:    host,
		Timeout: timeout,
		Workers: workers,
	}
}

func (s *Scanner) scanPort(port int) ScanResult {
	address := fmt.Sprintf("%s:%d", s.Host, port)
	conn, err := net.DialTimeout("tcp", address, s.Timeout)

	if err != nil {
		return ScanResult{Port: port, Status: "closed"}
	}

	conn.Close()
	return ScanResult{Port: port, Status: "open"}
}

func (s *Scanner) Scan(startPort, endPort int) []ScanResult {
	ports := make(chan int, endPort-startPort+1)
	results := make(chan ScanResult)
	var wg sync.WaitGroup

	for i := 0; i < s.Workers; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for port := range ports {
				results <- s.scanPort(port)
			}
		}()
	}

	go func() {
		for port := startPort; port <= endPort; port++ {
			ports <- port
		}
		close(ports)
	}()

	go func() {
		wg.Wait()
		close(results)
	}()

	var allResults []ScanResult
	for result := range results {
		allResults = append(allResults, result)
	}

	sort.Slice(allResults, func(i, j int) bool {
		return allResults[i].Port < allResults[j].Port
	})

	return allResults
}

func main() {
	host := flag.String("host", "localhost", "Target host to scan")
	startPort := flag.Int("start", 1, "Start port")
	endPort := flag.Int("end", 1024, "End port")
	timeout := flag.Duration("timeout", 1*time.Second, "Connection timeout")
	workers := flag.Int("workers", 100, "Number of concurrent workers")
	showClosed := flag.Bool("show-closed", false, "Show closed ports")
	verbose := flag.Bool("v", false, "Verbose output")

	flag.Parse()

	if *startPort < 1 || *startPort > 65535 {
		fmt.Println("Error: start port must be between 1 and 65535")
		os.Exit(1)
	}

	if *endPort < 1 || *endPort > 65535 {
		fmt.Println("Error: end port must be between 1 and 65535")
		os.Exit(1)
	}

	if *startPort > *endPort {
		fmt.Println("Error: start port cannot be greater than end port")
		os.Exit(1)
	}

	fmt.Printf("╔═══════════════════════════════════════════════╗\n")
	fmt.Printf("║         Port Scanner                          ║\n")
	fmt.Printf("╚═══════════════════════════════════════════════╝\n\n")
	fmt.Printf("Target:   %s\n", *host)
	fmt.Printf("Ports:    %d-%d (%d total)\n", *startPort, *endPort, *endPort-*startPort+1)
	fmt.Printf("Workers:  %d\n", *workers)
	fmt.Printf("Timeout:  %v\n", *timeout)
	fmt.Printf("\nScanning...\n\n")

	scanner := NewScanner(*host, *timeout, *workers)
	startTime := time.Now()
	results := scanner.Scan(*startPort, *endPort)
	elapsed := time.Since(startTime)

	openCount := 0
	closedCount := 0

	for _, result := range results {
		if result.Status == "open" {
			openCount++
		} else {
			closedCount++
		}
	}

	fmt.Printf("═══════════════════════════════════════════════\n")
	fmt.Printf("Results:\n")
	fmt.Printf("═══════════════════════════════════════════════\n\n")

	if openCount > 0 {
		fmt.Printf("Open ports (%d):\n", openCount)
		for _, result := range results {
			if result.Status == "open" {
				service := getServiceName(result.Port)
				if *verbose {
					fmt.Printf("  ✓ Port %5d  │  %-15s  │  %s\n", result.Port, result.Status, service)
				} else {
					fmt.Printf("  %5d/tcp  %s\n", result.Port, service)
				}
			}
		}
		fmt.Println()
	}

	if *showClosed && closedCount > 0 {
		fmt.Printf("Closed ports (%d):\n", closedCount)
		for _, result := range results {
			if result.Status == "closed" {
				if *verbose {
					fmt.Printf("  ✗ Port %5d  │  %s\n", result.Port, result.Status)
				}
			}
		}
		fmt.Println()
	}

	fmt.Printf("═══════════════════════════════════════════════\n")
	fmt.Printf("Statistics:\n")
	fmt.Printf("═══════════════════════════════════════════════\n")
	fmt.Printf("  Total ports scanned:  %d\n", len(results))
	fmt.Printf("  Open ports:           %d\n", openCount)
	fmt.Printf("  Closed ports:         %d\n", closedCount)
	fmt.Printf("  Scan duration:        %v\n", elapsed)
	fmt.Printf("  Ports per second:     %.2f\n", float64(len(results))/elapsed.Seconds())
}

func getServiceName(port int) string {
	services := map[int]string{
		20:    "FTP Data",
		21:    "FTP",
		22:    "SSH",
		23:    "Telnet",
		25:    "SMTP",
		53:    "DNS",
		80:    "HTTP",
		110:   "POP3",
		143:   "IMAP",
		443:   "HTTPS",
		445:   "SMB",
		3306:  "MySQL",
		3389:  "RDP",
		5432:  "PostgreSQL",
		6379:  "Redis",
		8080:  "HTTP-Alt",
		27017: "MongoDB",
	}

	if service, ok := services[port]; ok {
		return service
	}

	return "Unknown"
}
