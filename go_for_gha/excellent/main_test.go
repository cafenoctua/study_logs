package main


import "testing"


func TestEvenOrOdd(t *testing.T) {
	result := EvenOrOdd(10)
	if result != "event" {
		t.Errorf("excepted: event, actual: %s", result)
	}
}